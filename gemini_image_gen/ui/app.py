"""Gradio UI application for Gemini Image Generator"""

import gradio as gr
from typing import Tuple, List, Dict, Optional
from PIL import Image

from ..core import GeminiImageGenerator, ConversationManager
from ..utils import save_conversation, load_conversation, create_download_bytes, decode_image
from ..config import get_settings


def create_app():
    """Create and configure the Gradio application"""
    
    settings = get_settings()
    
    # Initialize components
    generator = GeminiImageGenerator()
    
    # Create interface
    with gr.Blocks(
        title="Gemini Image Generator",
        theme=gr.themes.Soft(),
        css="""
        .message-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            background: white;
            transition: all 0.3s ease;
        }
        .message-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .message-role {
            font-weight: bold;
            color: #333;
            margin-bottom: 4px;
        }
        .message-content {
            color: #666;
            margin: 8px 0;
        }
        .edited-indicator {
            color: #888;
            font-style: italic;
            font-size: 0.85em;
        }
        """
    ) as app:
        
        # Header
        gr.Markdown("""
        # 🎨 Gemini Image Generator
        ### Google Gemini APIを使用したインタラクティブ画像生成
        
        **機能:**
        - 💬 会話形式での画像生成
        - ✏️ 履歴の編集・削除
        - 💾 会話の保存・読み込み
        - 📥 生成画像のダウンロード
        """)
        
        # State management
        conversation_manager = gr.State(ConversationManager())
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
                
                # History display
                history_items = gr.Dataset(
                    components=[gr.Textbox(visible=False)],
                    samples=[],
                    label="履歴 (クリックして編集)",
                    type="index"
                )
                
                # Edit panel
                with gr.Group(visible=False) as edit_panel:
                    gr.Markdown("#### ✏️ メッセージを編集")
                    edit_text = gr.Textbox(
                        label="内容",
                        lines=3,
                        max_lines=10
                    )
                    with gr.Row():
                        save_edit_btn = gr.Button("保存", size="sm", variant="primary")
                        delete_btn = gr.Button("削除", size="sm", variant="stop")
                        cancel_btn = gr.Button("キャンセル", size="sm")
            
            # Right panel - Main interface
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="会話",
                    height=500,
                    type="messages",
                    show_copy_button=True
                )
                
                with gr.Group():
                    prompt_input = gr.Textbox(
                        label="プロンプト",
                        placeholder="画像を生成するプロンプトを入力...",
                        lines=3,
                        max_lines=5
                    )
                    
                    # Image upload for editing
                    upload_image = gr.Image(
                        label="画像をアップロード（編集用）",
                        type="pil",
                        visible=True
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
                
                # Image display
                with gr.Group(visible=False) as image_group:
                    gr.Markdown("### 🖼️ 生成された画像")
                    generated_image = gr.Image(
                        type="pil",
                        show_download_button=True
                    )
        
        # Status bar
        status = gr.Markdown("")
        
        # Event handlers
        def on_generate(
            prompt: str, 
            manager: ConversationManager,
            uploaded_image: Optional[Image.Image] = None,
            progress=gr.Progress()
        ):
            """Handle image generation"""
            if not prompt.strip():
                raise gr.Error("プロンプトを入力してください")
            
            try:
                settings.validate()
            except ValueError as e:
                raise gr.Error(str(e))
            
            progress(0.1, desc="処理中...")
            
            # Add user message
            manager.add_message("user", prompt)
            
            progress(0.3, desc="Gemini APIに接続中...")
            
            # Generate image
            generated_img, response_text = generator.generate(
                prompt, 
                manager.get_history(),
                uploaded_image
            )
            
            progress(0.8, desc="画像を処理中...")
            
            # Add model response
            manager.add_message("assistant", response_text, generated_img)
            
            progress(1.0, desc="完了！")
            
            # Update displays
            chat_display = format_history_for_display(manager.get_history())
            history_data = create_history_panel_data(manager.get_history())
            
            return (
                manager,
                chat_display,
                generated_img,
                gr.update(visible=generated_img is not None),
                "",
                None,  # Clear uploaded image
                gr.Dataset(samples=history_data),
                "✅ 生成完了"
            )
        
        def format_history_for_display(history: List[Dict]) -> List[Dict]:
            """Format history for chatbot display using messages format"""
            formatted = []
            
            for msg in history:
                if msg["role"] == "user":
                    content = msg["content"]
                    if msg.get("edited"):
                        content += "\n*(編集済み)*"
                    formatted.append({
                        "role": "user",
                        "content": content
                    })
                elif msg["role"] == "assistant" or msg["role"] == "model":
                    if "image" in msg:
                        # Create message with image using proper format
                        img = decode_image(msg["image"])
                        response_text = msg.get("content", "画像を生成しました")
                        
                        formatted.append({
                            "role": "assistant", 
                            "content": response_text,
                            "files": [img]
                        })
                    else:
                        formatted.append({
                            "role": "assistant",
                            "content": msg.get("content", "")
                        })
            
            return formatted
        
        def create_history_panel_data(history: List[Dict]) -> List[List[str]]:
            """Create dataset samples for history panel"""
            samples = []
            for i, msg in enumerate(history):
                role_emoji = "👤" if msg["role"] == "user" else "🤖"
                content_preview = msg.get("content", "")[:80]
                if len(msg.get("content", "")) > 80:
                    content_preview += "..."
                
                has_image = "🖼️ " if "image" in msg else ""
                edited = " ✏️" if msg.get("edited") else ""
                
                display = f"{role_emoji} {has_image}{content_preview}{edited}"
                samples.append([display])
            
            return samples
        
        def on_select_history(
            evt: gr.SelectData,
            manager: ConversationManager
        ):
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
        
        def on_save_edit(
            index: int,
            new_content: str,
            manager: ConversationManager
        ):
            """Save edited message"""
            if index is not None:
                manager.edit_message(index, new_content)
                chat_display = format_history_for_display(manager.get_history())
                history_data = create_history_panel_data(manager.get_history())
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=history_data),
                    gr.update(visible=False),
                    None,
                    "✅ 更新しました"
                )
            return manager, None, None, gr.update(visible=False), None, ""
        
        def on_delete(
            index: int,
            manager: ConversationManager
        ):
            """Delete message"""
            if index is not None:
                manager.delete_message(index)
                chat_display = format_history_for_display(manager.get_history())
                history_data = create_history_panel_data(manager.get_history())
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=history_data),
                    gr.update(visible=False),
                    None,
                    "✅ 削除しました"
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
                "✅ クリアしました"
            )
        
        def on_export(manager: ConversationManager):
            """Export conversation"""
            if not manager.get_history():
                raise gr.Error("履歴がありません")
            
            export_history = manager.get_exportable_history()
            filename = save_conversation(export_history)
            return filename, "✅ 保存しました"
        
        def on_import(file, manager: ConversationManager):
            """Import conversation"""
            if file:
                history = load_conversation(file)
                manager.load_from_export(history)
                chat_display = format_history_for_display(manager.get_history())
                history_data = create_history_panel_data(manager.get_history())
                
                return (
                    manager,
                    chat_display,
                    gr.Dataset(samples=history_data),
                    "✅ 読み込みました"
                )
            return manager, None, None, ""
        
        # Wire up events
        generate_btn.click(
            fn=on_generate,
            inputs=[prompt_input, conversation_manager, upload_image],
            outputs=[
                conversation_manager,
                chatbot,
                generated_image,
                image_group,
                prompt_input,
                upload_image,
                history_items,
                status
            ]
        )
        
        prompt_input.submit(
            fn=on_generate,
            inputs=[prompt_input, conversation_manager, upload_image],
            outputs=[
                conversation_manager,
                chatbot,
                generated_image,
                image_group,
                prompt_input,
                upload_image,
                history_items,
                status
            ]
        )
        
        history_items.select(
            fn=on_select_history,
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


def launch_app():
    """Launch the Gradio application"""
    settings = get_settings()
    app = create_app()
    
    app.launch(
        server_name=settings.host,
        server_port=settings.port,
        share=settings.share,
        show_error=True,
        inbrowser=False  # WSLではブラウザが開けないのでFalseに変更
    )


if __name__ == "__main__":
    launch_app()