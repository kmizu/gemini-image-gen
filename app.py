import os
import base64
import mimetypes
import gradio as gr
from google import genai
from google.genai import types
from PIL import Image
import io
from typing import List, Tuple, Dict, Any
import json
from datetime import datetime

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-image-preview"

def generate_image(prompt: str, conversation_history: List[Dict]) -> Tuple[Image.Image, str]:
    """Generate image using Gemini API with conversation history"""
    
    # Build contents from conversation history
    contents = []
    for msg in conversation_history:
        if msg["role"] == "user":
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        elif msg["role"] == "model" and msg.get("content"):
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_text(text=msg["content"])] if msg["content"] else []
            ))
    
    # Add current prompt
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    ))
    
    # Configure generation
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    )
    
    # Generate content
    generated_image = None
    response_text = ""
    
    try:
        for chunk in client.models.generate_content_stream(
            model=MODEL,
            contents=contents,
            config=generate_content_config,
        ):
            if (chunk.candidates is None or 
                chunk.candidates[0].content is None or 
                chunk.candidates[0].content.parts is None):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            
            # Handle image data
            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                inline_data = part.inline_data
                image = Image.open(io.BytesIO(inline_data.data))
                generated_image = image
            # Handle text response
            elif hasattr(part, 'text') and part.text:
                response_text += part.text
    
    except Exception as e:
        raise gr.Error(f"画像生成エラー: {str(e)}")
    
    return generated_image, response_text

def add_message_to_history(history: List, role: str, content: str = None, image: Image.Image = None):
    """Add a message to conversation history"""
    message = {"role": role, "content": content}
    if image:
        # Convert image to base64 for storage
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        message["image"] = img_str
    history.append(message)
    return history

def format_chat_history(history: List) -> List[Tuple]:
    """Format history for Gradio Chatbot component"""
    chat_display = []
    for msg in history:
        if msg["role"] == "user":
            chat_display.append((msg["content"], None))
        elif msg["role"] == "model":
            # Display image if available
            if "image" in msg:
                img_data = base64.b64decode(msg["image"])
                img = Image.open(io.BytesIO(img_data))
                response = msg.get("content", "")
                chat_display.append((None, (img, response)))
            else:
                chat_display.append((None, msg.get("content", "")))
    return chat_display

def clear_history():
    """Clear all conversation history"""
    return [], [], None, None

def delete_message(history: List, index: int) -> Tuple[List, List]:
    """Delete a specific message from history"""
    if 0 <= index < len(history):
        history.pop(index)
    return history, format_chat_history(history)

def edit_message(history: List, index: int, new_content: str) -> Tuple[List, List]:
    """Edit a specific message in history"""
    if 0 <= index < len(history):
        history[index]["content"] = new_content
    return history, format_chat_history(history)

def generate_and_update(prompt: str, history: List, progress=gr.Progress()):
    """Generate image and update conversation"""
    if not prompt.strip():
        raise gr.Error("プロンプトを入力してください")
    
    if not os.environ.get("GEMINI_API_KEY"):
        raise gr.Error("GEMINI_API_KEY環境変数が設定されていません")
    
    progress(0.2, desc="画像を生成中...")
    
    # Add user message to history
    history = add_message_to_history(history, "user", prompt)
    
    # Generate image
    progress(0.5, desc="Gemini APIを呼び出し中...")
    generated_image, response_text = generate_image(prompt, history)
    
    if generated_image:
        # Add model response with image to history
        history = add_message_to_history(history, "model", response_text, generated_image)
        progress(1.0, desc="完了！")
        
        # Create downloadable image
        buffered = io.BytesIO()
        generated_image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        return (
            history, 
            format_chat_history(history), 
            generated_image,
            img_bytes,
            ""  # Clear input
        )
    else:
        # Add text-only response
        history = add_message_to_history(history, "model", response_text)
        return (
            history,
            format_chat_history(history),
            None,
            None,
            ""
        )

def create_history_editor(history: List) -> str:
    """Create HTML for history editor with edit/delete buttons"""
    if not history:
        return "<p>履歴がありません</p>"
    
    html = "<div style='max-height: 400px; overflow-y: auto;'>"
    for i, msg in enumerate(history):
        role_label = "👤 User" if msg["role"] == "user" else "🤖 Model"
        content = msg.get("content", "")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", "")
        
        html += f"""
        <div style='border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;'>
            <div style='font-weight: bold;'>{role_label}</div>
            <div style='margin: 5px 0;'>{content}</div>
            <div style='margin-top: 10px;'>
                <button onclick='editMessage({i})'>編集</button>
                <button onclick='deleteMessage({i})' style='margin-left: 10px; color: red;'>削除</button>
            </div>
        </div>
        """
    html += "</div>"
    return html

def save_history_to_file(history: List) -> str:
    """Save conversation history to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_history_{timestamp}.json"
    
    # Remove image data for file export (too large)
    export_history = []
    for msg in history:
        export_msg = {"role": msg["role"], "content": msg.get("content", "")}
        if "image" in msg:
            export_msg["has_image"] = True
        export_history.append(export_msg)
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(export_history, f, ensure_ascii=False, indent=2)
    
    return filename

def load_history_from_file(file):
    """Load conversation history from JSON file"""
    if file is None:
        return [], []
    
    with open(file.name, "r", encoding="utf-8") as f:
        loaded_history = json.load(f)
    
    # Convert to internal format
    history = []
    for msg in loaded_history:
        history.append({
            "role": msg["role"],
            "content": msg.get("content", "")
        })
    
    return history, format_chat_history(history)

# Create Gradio interface
with gr.Blocks(title="Gemini Image Generator", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎨 Gemini Image Generator")
    gr.Markdown("Google Gemini APIを使用した対話型画像生成アプリケーション")
    
    # State for conversation history
    conversation_state = gr.State([])
    
    with gr.Row():
        # Left column - History management
        with gr.Column(scale=1):
            gr.Markdown("### 📝 会話履歴管理")
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ 履歴クリア", variant="stop", scale=1)
                export_btn = gr.Button("💾 エクスポート", scale=1)
            
            import_file = gr.File(label="履歴をインポート", file_types=[".json"])
            
            history_display = gr.HTML(value="<p>履歴がありません</p>")
            
            # History item editor (hidden by default)
            with gr.Group(visible=False) as editor_group:
                gr.Markdown("#### 編集")
                edit_index = gr.Number(visible=False)
                edit_content = gr.Textbox(label="内容", lines=3)
                with gr.Row():
                    save_edit_btn = gr.Button("保存", variant="primary")
                    cancel_edit_btn = gr.Button("キャンセル")
        
        # Right column - Chat interface
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="会話",
                height=400,
                bubble_full_width=False,
                type="tuples"
            )
            
            with gr.Row():
                prompt_input = gr.Textbox(
                    label="プロンプト",
                    placeholder="画像生成プロンプトを入力してください...",
                    lines=2,
                    scale=4
                )
                generate_btn = gr.Button("🎨 生成", variant="primary", scale=1)
            
            with gr.Row():
                generated_image = gr.Image(
                    label="生成画像",
                    type="pil",
                    visible=False
                )
                download_file = gr.File(
                    label="ダウンロード",
                    visible=False
                )
    
    # Status display
    status_text = gr.Markdown("")
    
    # Event handlers
    def update_history_display(history):
        """Update the history display HTML"""
        return create_history_editor(history)
    
    def show_editor(index, history):
        """Show editor for a specific message"""
        if 0 <= index < len(history):
            return gr.update(visible=True), history[index].get("content", "")
        return gr.update(visible=False), ""
    
    def hide_editor():
        """Hide the editor"""
        return gr.update(visible=False), ""
    
    # Connect events
    generate_btn.click(
        fn=generate_and_update,
        inputs=[prompt_input, conversation_state],
        outputs=[
            conversation_state,
            chatbot,
            generated_image,
            download_file,
            prompt_input
        ]
    ).then(
        fn=lambda img: gr.update(visible=img is not None),
        inputs=[generated_image],
        outputs=[generated_image]
    ).then(
        fn=lambda file: gr.update(visible=file is not None),
        inputs=[download_file],
        outputs=[download_file]
    ).then(
        fn=update_history_display,
        inputs=[conversation_state],
        outputs=[history_display]
    )
    
    # Also trigger on Enter key
    prompt_input.submit(
        fn=generate_and_update,
        inputs=[prompt_input, conversation_state],
        outputs=[
            conversation_state,
            chatbot,
            generated_image,
            download_file,
            prompt_input
        ]
    ).then(
        fn=lambda img: gr.update(visible=img is not None),
        inputs=[generated_image],
        outputs=[generated_image]
    ).then(
        fn=lambda file: gr.update(visible=file is not None),
        inputs=[download_file],
        outputs=[download_file]
    ).then(
        fn=update_history_display,
        inputs=[conversation_state],
        outputs=[history_display]
    )
    
    clear_btn.click(
        fn=clear_history,
        outputs=[conversation_state, chatbot, generated_image, download_file]
    ).then(
        fn=update_history_display,
        inputs=[conversation_state],
        outputs=[history_display]
    )
    
    export_btn.click(
        fn=save_history_to_file,
        inputs=[conversation_state],
        outputs=[gr.File(label="エクスポートファイル")]
    )
    
    import_file.upload(
        fn=load_history_from_file,
        inputs=[import_file],
        outputs=[conversation_state, chatbot]
    ).then(
        fn=update_history_display,
        inputs=[conversation_state],
        outputs=[history_display]
    )
    
    # Editor events
    save_edit_btn.click(
        fn=edit_message,
        inputs=[conversation_state, edit_index, edit_content],
        outputs=[conversation_state, chatbot]
    ).then(
        fn=hide_editor,
        outputs=[editor_group]
    ).then(
        fn=update_history_display,
        inputs=[conversation_state],
        outputs=[history_display]
    )
    
    cancel_edit_btn.click(
        fn=hide_editor,
        outputs=[editor_group]
    )

if __name__ == "__main__":
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )