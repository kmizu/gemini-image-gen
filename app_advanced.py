import os
import base64
import mimetypes
import gradio as gr
from google import genai
from google.genai import types
from PIL import Image
import io
from typing import List, Tuple, Dict, Any, Optional
import json
from datetime import datetime
import tempfile

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-image-preview"

class ConversationManager:
    """Manage conversation history with edit and delete capabilities"""
    
    def __init__(self):
        self.history: List[Dict] = []
    
    def add_message(self, role: str, content: str = None, image: Image.Image = None) -> List[Dict]:
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if image:
            # Convert image to base64 for storage
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            message["image"] = img_str
        self.history.append(message)
        return self.history
    
    def delete_message(self, index: int) -> List[Dict]:
        """Delete a specific message from history"""
        if 0 <= index < len(self.history):
            self.history.pop(index)
        return self.history
    
    def edit_message(self, index: int, new_content: str) -> List[Dict]:
        """Edit a specific message in history"""
        if 0 <= index < len(self.history):
            self.history[index]["content"] = new_content
            self.history[index]["edited"] = True
            self.history[index]["edit_timestamp"] = datetime.now().isoformat()
        return self.history
    
    def clear_history(self):
        """Clear all conversation history"""
        self.history = []
        return self.history
    
    def get_history(self) -> List[Dict]:
        """Get current history"""
        return self.history
    
    def set_history(self, history: List[Dict]):
        """Set history from external source"""
        self.history = history

def generate_image_with_history(prompt: str, history: List[Dict]) -> Tuple[Optional[Image.Image], str]:
    """Generate image using Gemini API with conversation history"""
    
    # Build contents from conversation history
    contents = []
    for msg in history[:-1]:  # Exclude the current message we just added
        if msg["role"] == "user":
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        elif msg["role"] == "model" and msg.get("content"):
            # Only add model responses with text content
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
        temperature=0.3,
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

def format_history_for_display(history: List[Dict]) -> List[Tuple]:
    """Format history for Gradio Chatbot display"""
    formatted = []
    
    for msg in history:
        if msg["role"] == "user":
            # User message
            content = msg["content"]
            if msg.get("edited"):
                content = f"{content}\n*(編集済み)*"
            formatted.append((content, None))
        elif msg["role"] == "model":
            # Model response
            if "image" in msg:
                # Decode and display image
                img_data = base64.b64decode(msg["image"])
                img = Image.open(io.BytesIO(img_data))
                response_text = msg.get("content", "")
                formatted.append((None, (img, response_text)))
            else:
                # Text only response
                formatted.append((None, msg.get("content", "")))
    
    return formatted

def create_editable_history_panel(history: List[Dict]) -> List[gr.Row]:
    """Create an editable history panel with individual message controls"""
    components = []
    
    for i, msg in enumerate(history):
        role_emoji = "👤" if msg["role"] == "user" else "🤖"
        content_preview = msg.get("content", "")[:100]
        if len(msg.get("content", "")) > 100:
            content_preview += "..."
        
        # Check if message has image
        has_image = "image" in msg
        image_indicator = "🖼️ " if has_image else ""
        
        # Check if edited
        edited_indicator = " ✏️" if msg.get("edited") else ""
        
        display_text = f"{role_emoji} {image_indicator}{content_preview}{edited_indicator}"
        
        components.append({
            "index": i,
            "role": msg["role"],
            "content": msg.get("content", ""),
            "display": display_text,
            "has_image": has_image,
            "edited": msg.get("edited", False)
        })
    
    return components

def save_conversation(manager: ConversationManager) -> str:
    """Save conversation to file and return filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_{timestamp}.json"
    
    # Prepare history for export (remove large image data)
    export_history = []
    for msg in manager.get_history():
        export_msg = {
            "role": msg["role"],
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp", ""),
        }
        if "image" in msg:
            export_msg["has_image"] = True
        if msg.get("edited"):
            export_msg["edited"] = True
            export_msg["edit_timestamp"] = msg.get("edit_timestamp", "")
        export_history.append(export_msg)
    
    # Save to temporary file for download
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(export_history, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    
    return temp_file.name

def load_conversation(file, manager: ConversationManager) -> Tuple[ConversationManager, List]:
    """Load conversation from file"""
    if file is None:
        return manager, []
    
    try:
        with open(file.name, "r", encoding="utf-8") as f:
            loaded_history = json.load(f)
        
        # Convert to internal format
        new_history = []
        for msg in loaded_history:
            history_msg = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            if msg.get("edited"):
                history_msg["edited"] = True
                history_msg["edit_timestamp"] = msg.get("edit_timestamp", "")
            new_history.append(history_msg)
        
        manager.set_history(new_history)
        return manager, format_history_for_display(new_history)
    
    except Exception as e:
        raise gr.Error(f"ファイル読み込みエラー: {str(e)}")

# Create the Gradio interface
def create_interface():
    manager = ConversationManager()
    
    with gr.Blocks(title="Gemini Image Generator", theme=gr.themes.Soft(), css="""
        .message-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            margin: 5px 0;
            background: white;
        }
        .message-role {
            font-weight: bold;
            color: #333;
        }
        .message-content {
            margin: 8px 0;
            color: #666;
        }
        .message-actions {
            margin-top: 8px;
        }
        .edited-indicator {
            color: #888;
            font-style: italic;
            font-size: 0.9em;
        }
    """) as app:
        
        gr.Markdown("""
        # 🎨 Gemini Image Generator
        ### インタラクティブな画像生成アプリケーション
        
        **機能:**
        - 💬 対話形式での画像生成
        - ✏️ 会話履歴の編集・削除
        - 💾 会話の保存・読み込み
        - 📥 生成画像のダウンロード
        """)
        
        # State management
        conversation_manager = gr.State(manager)
        selected_index = gr.State(None)
        
        with gr.Row():
            # Left panel - History management
            with gr.Column(scale=1):
                gr.Markdown("### 📝 会話履歴")
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ クリア", size="sm", variant="stop")
                    export_btn = gr.Button("💾 保存", size="sm")
                
                import_file = gr.File(
                    label="会話を読み込む",
                    file_types=[".json"],
                    type="filepath"
                )
                
                # History list with edit/delete functionality
                with gr.Column() as history_panel:
                    history_items = gr.Dataset(
                        components=[gr.Textbox(visible=False)],
                        samples=[],
                        label="履歴項目 (クリックして編集)",
                        type="index"
                    )
                    
                    with gr.Group(visible=False) as edit_panel:
                        gr.Markdown("#### ✏️ メッセージを編集")
                        edit_text = gr.Textbox(
                            label="内容",
                            lines=3,
                            max_lines=10
                        )
                        with gr.Row():
                            save_edit_btn = gr.Button("💾 保存", size="sm", variant="primary")
                            delete_btn = gr.Button("🗑️ 削除", size="sm", variant="stop")
                            cancel_btn = gr.Button("キャンセル", size="sm")
            
            # Right panel - Main chat interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="会話",
                    height=500,
                    bubble_full_width=False,
                    avatar_images=(None, None),
                    show_copy_button=True
                )
                
                with gr.Group():
                    prompt_input = gr.Textbox(
                        label="プロンプト",
                        placeholder="画像を生成するプロンプトを入力してください...",
                        lines=3,
                        max_lines=5
                    )
                    
                    with gr.Row():
                        generate_btn = gr.Button(
                            "🎨 画像を生成",
                            variant="primary",
                            scale=2
                        )
                        stop_btn = gr.Button(
                            "⏹️ 停止",
                            variant="stop",
                            scale=1,
                            visible=False
                        )
                
                # Generated image display
                with gr.Group(visible=False) as image_group:
                    gr.Markdown("### 🖼️ 生成された画像")
                    generated_image = gr.Image(
                        type="pil",
                        show_download_button=True,
                        show_share_button=False
                    )
        
        # Status bar
        status = gr.Markdown("")
        
        # Event handlers
        def on_generate(prompt: str, manager: ConversationManager, progress=gr.Progress()):
            """Handle image generation"""
            if not prompt.strip():
                raise gr.Error("プロンプトを入力してください")
            
            if not os.environ.get("GEMINI_API_KEY"):
                raise gr.Error("GEMINI_API_KEY環境変数が設定されていません")
            
            progress(0.1, desc="リクエストを処理中...")
            
            # Add user message
            manager.add_message("user", prompt)
            chat_display = format_history_for_display(manager.get_history())
            
            progress(0.3, desc="Gemini APIに接続中...")
            
            # Generate image
            try:
                generated_img, response_text = generate_image_with_history(prompt, manager.get_history())
                
                progress(0.8, desc="画像を処理中...")
                
                # Add model response
                manager.add_message("model", response_text, generated_img)
                chat_display = format_history_for_display(manager.get_history())
                
                progress(1.0, desc="完了！")
                
                # Update history panel
                history_data = create_editable_history_panel(manager.get_history())
                samples = [[item["display"]] for item in history_data]
                
                if generated_img:
                    return (
                        manager,
                        chat_display,
                        generated_img,
                        gr.update(visible=True),
                        "",
                        gr.Dataset(samples=samples),
                        "✅ 画像が生成されました"
                    )
                else:
                    return (
                        manager,
                        chat_display,
                        None,
                        gr.update(visible=False),
                        "",
                        gr.Dataset(samples=samples),
                        "✅ レスポンスを受信しました"
                    )
            
            except Exception as e:
                progress(1.0)
                raise gr.Error(f"生成エラー: {str(e)}")
        
        def on_select_history_item(evt: gr.SelectData, manager: ConversationManager):
            """Handle history item selection"""
            index = evt.index[0] if evt.index else None
            if index is not None and 0 <= index < len(manager.get_history()):
                msg = manager.get_history()[index]
                return (
                    index,
                    gr.update(visible=True),
                    msg.get("content", "")
                )
            return None, gr.update(visible=False), ""
        
        def on_save_edit(index: int, new_content: str, manager: ConversationManager):
            """Save edited message"""
            if index is not None:
                manager.edit_message(index, new_content)
                chat_display = format_history_for_display(manager.get_history())
                history_data = create_editable_history_panel(manager.get_history())
                samples = [[item["display"]] for item in history_data]
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=samples),
                    gr.update(visible=False),
                    None,
                    "✅ メッセージを更新しました"
                )
            return manager, None, None, gr.update(visible=False), None, ""
        
        def on_delete(index: int, manager: ConversationManager):
            """Delete message"""
            if index is not None:
                manager.delete_message(index)
                chat_display = format_history_for_display(manager.get_history())
                history_data = create_editable_history_panel(manager.get_history())
                samples = [[item["display"]] for item in history_data]
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=samples),
                    gr.update(visible=False),
                    None,
                    "✅ メッセージを削除しました"
                )
            return manager, None, None, gr.update(visible=False), None, ""
        
        def on_clear(manager: ConversationManager):
            """Clear all history"""
            manager.clear_history()
            return (
                manager,
                [],
                gr.Dataset(samples=[]),
                None,
                gr.update(visible=False),
                "✅ 履歴をクリアしました"
            )
        
        def on_export(manager: ConversationManager):
            """Export conversation"""
            if not manager.get_history():
                raise gr.Error("エクスポートする履歴がありません")
            
            filename = save_conversation(manager)
            return filename, "✅ 会話を保存しました"
        
        def on_import(file, manager: ConversationManager):
            """Import conversation"""
            if file:
                manager, chat_display = load_conversation(file, manager)
                history_data = create_editable_history_panel(manager.get_history())
                samples = [[item["display"]] for item in history_data]
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=samples),
                    "✅ 会話を読み込みました"
                )
            return manager, None, None, ""
        
        # Wire up events
        generate_btn.click(
            fn=on_generate,
            inputs=[prompt_input, conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                generated_image,
                image_group,
                prompt_input,
                history_items,
                status
            ]
        )
        
        prompt_input.submit(
            fn=on_generate,
            inputs=[prompt_input, conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                generated_image,
                image_group,
                prompt_input,
                history_items,
                status
            ]
        )
        
        history_items.select(
            fn=on_select_history_item,
            inputs=[conversation_manager],
            outputs=[selected_index, edit_panel, edit_text]
        )
        
        save_edit_btn.click(
            fn=on_save_edit,
            inputs=[selected_index, edit_text, conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                history_items,
                edit_panel,
                selected_index,
                status
            ]
        )
        
        delete_btn.click(
            fn=on_delete,
            inputs=[selected_index, conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                history_items,
                edit_panel,
                selected_index,
                status
            ]
        )
        
        cancel_btn.click(
            fn=lambda: (gr.update(visible=False), None),
            outputs=[edit_panel, selected_index]
        )
        
        clear_btn.click(
            fn=on_clear,
            inputs=[conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                history_items,
                generated_image,
                image_group,
                status
            ]
        )
        
        export_btn.click(
            fn=on_export,
            inputs=[conversation_manager],
            outputs=[gr.File(label="ダウンロード"), status]
        )
        
        import_file.upload(
            fn=on_import,
            inputs=[import_file, conversation_manager],
            outputs=[
                conversation_manager,
                chatbot,
                history_items,
                status
            ]
        )
    
    return app

if __name__ == "__main__":
    app = create_interface()
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        inbrowser=True
    )
