"""Gradio UI application with batch generation support"""

import gradio as gr
from typing import Tuple, List, Dict, Optional, Any
from PIL import Image

from ..core import GeminiImageGenerator, ConversationManager
from ..utils import (
    save_conversation, load_conversation, create_download_bytes, decode_image,
    create_batch_zip, save_image_with_metadata, cleanup_temp_files,
    BatchGenerationResult, generate_prompt_combinations, validate_combination_inputs,
    create_combination_summary
)
from ..config import get_settings
# from .components import BatchImageMatrix, BatchGenerationSettings


def create_batch_app():
    """Create and configure the Gradio application with batch support"""

    settings = get_settings()

    # Initialize components
    generator = GeminiImageGenerator()

    # Create interface
    with gr.Blocks(
        title="Gemini Image Generator - Batch",
        theme=gr.themes.Soft(),
        analytics_enabled=False,
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
        .batch-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .batch-item {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            background: white;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .batch-item:hover {
            border-color: #007bff;
            box-shadow: 0 4px 12px rgba(0,123,255,0.15);
        }
        .batch-item.selected {
            border-color: #28a745;
            background: #f8fff9;
        }
        .batch-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 4px;
            margin-bottom: 8px;
        }
        """
    ) as app:

        # Header
        gr.Markdown("""
        # 🎨 Gemini Image Generator - Batch Edition
        ### Google Gemini APIを使用したバッチ画像生成

        **新機能:**
        - 🔢 **バッチ生成**: 1つのプロンプトから複数枚を同時生成
        - ⚡ **並列処理**: 高速な画像生成
        - 📦 **一括ダウンロード**: ZIP形式での一括保存
        - 🖱️ **画像選択**: 生成結果から好みの画像を選択
        """)

        # State management
        conversation_manager = gr.State(ConversationManager())
        selected_index = gr.State(None)

        # Batch settings
        def create_batch_settings():
            """Create batch generation settings panel"""
            with gr.Group() as settings_group:
                gr.Markdown("### ⚙️ バッチ生成設定")

                with gr.Row():
                    batch_size_slider = gr.Slider(
                        minimum=1,
                        maximum=settings.max_batch_size,
                        value=settings.default_batch_size,
                        step=1,
                        label="生成枚数",
                        info=f"1-{settings.max_batch_size}枚"
                    )

                    parallel_checkbox = gr.Checkbox(
                        label="並列生成",
                        value=True,
                        info="高速化（推奨）"
                    )

                with gr.Row():
                    enable_batch_checkbox = gr.Checkbox(
                        label="バッチ生成を有効化",
                        value=True,
                        info="チェックすると複数枚生成"
                    )

            return settings_group, batch_size_slider, parallel_checkbox, enable_batch_checkbox

        with gr.Row():
            # Left panel - Settings and History
            with gr.Column(scale=1):
                # Batch settings
                settings_group, batch_size_slider, parallel_checkbox, enable_batch_checkbox = create_batch_settings()

                gr.Markdown("### 📝 会話履歴管理")

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
                # Chat display
                chatbot = gr.Chatbot(
                    label="会話",
                    height=400,
                    type="messages",
                    show_copy_button=True
                )

                # Input section
                with gr.Group():
                    with gr.Tab("📝 通常プロンプト"):
                        prompt_input = gr.Textbox(
                            label="プロンプト",
                            placeholder="画像を生成するプロンプトを入力...",
                            lines=3,
                            max_lines=5
                        )

                    with gr.Tab("🔀 プロンプト組み合わせ（16通り生成）"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("**ベースプロンプト:**")
                                base_prompt = gr.Textbox(
                                    label="ベース",
                                    placeholder="共通のベースプロンプト...",
                                    lines=2
                                )

                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("**組み合わせ要素A:**")
                                combo_a1 = gr.Textbox(label="A1", placeholder="要素A-1...")
                                combo_a2 = gr.Textbox(label="A2", placeholder="要素A-2...")
                                combo_a3 = gr.Textbox(label="A3", placeholder="要素A-3...")
                                combo_a4 = gr.Textbox(label="A4", placeholder="要素A-4...")

                            with gr.Column():
                                gr.Markdown("**組み合わせ要素B:**")
                                combo_b1 = gr.Textbox(label="B1", placeholder="要素B-1...")
                                combo_b2 = gr.Textbox(label="B2", placeholder="要素B-2...")
                                combo_b3 = gr.Textbox(label="B3", placeholder="要素B-3...")
                                combo_b4 = gr.Textbox(label="B4", placeholder="要素B-4...")

                        combination_mode = gr.Checkbox(
                            label="🔀 組み合わせモードを有効にする（16通り生成）",
                            value=False
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
                        cancel_generation_btn = gr.Button(
                            "⏹️ 生成停止",
                            variant="stop",
                            scale=1,
                            visible=False
                        )

                # Batch results display
                with gr.Group(visible=False) as batch_results_group:
                    gr.Markdown("### 🖼️ 生成された画像")

                    # Batch images gallery
                    batch_gallery = gr.Gallery(
                        label="生成結果",
                        show_label=True,
                        elem_id="batch_gallery",
                        columns=4,
                        rows=2,
                        height="auto",
                        allow_preview=True,
                        preview=True
                    )

                    # Batch controls
                    with gr.Row():
                        batch_download_btn = gr.Button(
                            "📦 全画像をZIPダウンロード",
                            variant="primary"
                        )
                        clear_batch_btn = gr.Button(
                            "🗑️ バッチクリア",
                            variant="secondary"
                        )

                    # Hidden states for batch data
                    batch_images_state = gr.State([])
                    batch_texts_state = gr.State([])

                    # File output for downloads
                    with gr.Row(visible=False) as download_row:
                        gr.Markdown("### 📦 ダウンロード")
                        download_file = gr.File(
                            label="ZIPファイル",
                            visible=True,
                            interactive=True,
                            show_label=True,
                            file_count="single"
                        )

        # Status bar
        status = gr.Markdown("")

        # Event handlers
        def on_generate_batch(
            prompt: str,
            manager: ConversationManager,
            batch_size: int,
            use_parallel: bool,
            enable_batch: bool,
            # Combination mode parameters
            combination_mode: bool,
            base_prompt: str,
            combo_a1: str, combo_a2: str, combo_a3: str, combo_a4: str,
            combo_b1: str, combo_b2: str, combo_b3: str, combo_b4: str,
            uploaded_image: Optional[Image.Image] = None,
            progress=gr.Progress()
        ):
            """Handle batch image generation"""
            print(f"🔧 DEBUG: on_generate_batch呼び出し")
            print(f"🔧 DEBUG: 引数タイプ - prompt: {type(prompt)}, manager: {type(manager)}, batch_size: {type(batch_size)}")
            print(f"🔧 DEBUG: checkbox値 - use_parallel: {use_parallel} ({type(use_parallel)}), enable_batch: {enable_batch} ({type(enable_batch)})")
            print(f"📝 DEBUG: プロンプト='{prompt}', プロンプト長さ={len(prompt) if prompt else 0}, 画像アップロード={'あり' if uploaded_image else 'なし'}")
            print(f"📝 DEBUG: プロンプトはNone? {prompt is None}, プロンプトは空文字? {prompt == ''}, strip後空? {not prompt.strip() if prompt else 'N/A'}")

            # Handle potential None values from checkboxes
            use_parallel = bool(use_parallel) if use_parallel is not None else False
            enable_batch = bool(enable_batch) if enable_batch is not None else False

            # Ensure prompt is a string
            if prompt is None:
                prompt = ""

            print(f"🔧 DEBUG: 正規化後 - enable_batch={enable_batch}, use_parallel={use_parallel}")
            print(f"🔀 DEBUG: 組み合わせモード - {combination_mode}")

            # Check if combination inputs are provided (auto-detect combination mode)
            combo_a_list = [combo_a1, combo_a2, combo_a3, combo_a4]
            combo_b_list = [combo_b1, combo_b2, combo_b3, combo_b4]
            has_combination_inputs = any(a.strip() for a in combo_a_list) or any(b.strip() for b in combo_b_list)

            # Auto-enable combination mode if combination inputs are provided
            if has_combination_inputs and not combination_mode:
                print(f"🔀 DEBUG: 組み合わせ入力を検出、自動で組み合わせモードを有効化")
                combination_mode = True

            # Handle combination mode
            if combination_mode:
                print(f"🔀 DEBUG: 組み合わせモードが有効です")

                is_valid, error_msg = validate_combination_inputs(base_prompt, combo_a_list, combo_b_list)
                if not is_valid:
                    raise gr.Error(error_msg)

                # Generate combinations
                combinations = generate_prompt_combinations(base_prompt, combo_a_list, combo_b_list)
                total_combinations = len(combinations)

                print(f"🔀 DEBUG: {total_combinations}通りの組み合わせを生成します")

                # Override batch settings for combination mode
                enable_batch = True
                actual_batch_size = total_combinations

                # Show combination summary
                combination_summary = create_combination_summary(base_prompt, combo_a_list, combo_b_list)
                progress(0.1, desc=f"組み合わせ生成準備中: {total_combinations}通り")

            else:
                print(f"📝 DEBUG: 通常モードです")
                # Normal mode validation - only check prompt if not in combination mode
                if not prompt or not prompt.strip():
                    print(f"❌ DEBUG: プロンプト検証失敗 - '{prompt}'")
                    raise gr.Error(f"通常モードではプロンプトを入力してください。組み合わせ生成を使用する場合は「🔀 プロンプト組み合わせ」タブで要素を入力してください。")
                actual_batch_size = batch_size if enable_batch else 1

            try:
                settings.validate()
            except ValueError as e:
                raise gr.Error(str(e))

            # Add user message
            if combination_mode:
                manager.add_message("user", f"組み合わせ生成: {combination_summary}")
            else:
                manager.add_message("user", prompt)

            progress(0.2, desc=f"画像生成中: {actual_batch_size}枚 ({'組み合わせ' if combination_mode else 'バッチ'}{'有効' if enable_batch else '無効'})")

            try:
                if not enable_batch or actual_batch_size == 1:
                    # Single generation
                    generated_img, response_text = generator.generate(
                        prompt,
                        manager.get_history(),
                        uploaded_image
                    )

                    if generated_img:
                        # Add to conversation
                        manager.add_message("assistant", response_text, generated_img)

                        # Update displays
                        chat_display = format_history_for_display(manager.get_history())
                        history_data = create_history_panel_data(manager.get_history())

                        # Show single image in gallery
                        return (
                            manager,
                            chat_display,
                            "",  # Clear prompt
                            None,  # Clear uploaded image
                            gr.Dataset(samples=history_data),
                            gr.update(visible=True),  # batch_results_group
                            [generated_img],  # batch_gallery
                            [generated_img],  # batch_images_state
                            [response_text],  # batch_texts_state
                            "✅ 画像を生成しました"
                        )
                else:
                    # Batch generation
                    if combination_mode:
                        progress(0.25, desc=f"組み合わせ生成開始: {actual_batch_size}通り")

                        # Generate images for each combination
                        batch_images = []
                        batch_texts = []
                        failed_count = 0

                        for i, (combo_prompt, combo_desc) in enumerate(combinations):
                            try:
                                progress(0.2 + (i / len(combinations)) * 0.7,
                                        desc=f"生成中 {i+1}/{len(combinations)}: {combo_desc}")

                                generated_img, response_text = generator.generate(
                                    combo_prompt,
                                    manager.get_history(),
                                    uploaded_image
                                )

                                if generated_img:
                                    batch_images.append(generated_img)
                                    batch_texts.append(combo_desc)
                                else:
                                    failed_count += 1

                            except Exception as e:
                                print(f"❌ 組み合わせ {i+1} 生成失敗: {str(e)}")
                                failed_count += 1

                        # Create batch result object
                        class CombinationResult:
                            def __init__(self, images, texts, failed_count):
                                self.success_images = images
                                self.success_texts = texts
                                self.successful_count = len(images)
                                self.failed_count = failed_count

                            def get_summary(self):
                                return f"組み合わせ生成完了: {self.successful_count}枚"

                        batch_result = CombinationResult(batch_images, batch_texts, failed_count)
                    else:
                        progress(0.25, desc=f"バッチ生成開始: {actual_batch_size}枚")
                        def progress_callback(prog: float, desc: str):
                            progress(0.2 + prog * 0.7, desc)

                        batch_result = generator.generate_batch(
                            prompt=prompt,
                            conversation_history=manager.get_history(),
                            input_image=uploaded_image,
                            batch_size=actual_batch_size,
                            use_parallel=use_parallel,
                            progress_callback=progress_callback
                        )

                    progress(0.9, desc="結果を処理中...")

                    if batch_result.successful_count > 0:
                        # Add batch result to conversation
                        manager.add_batch_result(
                            "assistant",
                            batch_result.success_images,
                            batch_result.success_texts
                        )

                        # Update displays
                        chat_display = format_history_for_display(manager.get_history())
                        history_data = create_history_panel_data(manager.get_history())

                        progress(1.0, desc="完了!")

                        status_msg = batch_result.get_summary()
                        if batch_result.failed_count > 0:
                            status_msg += f" (失敗: {batch_result.failed_count}枚)"

                        return (
                            manager,
                            chat_display,
                            "",  # Clear prompt
                            None,  # Clear uploaded image
                            gr.Dataset(samples=history_data),
                            gr.update(visible=True),  # batch_results_group
                            batch_result.success_images,  # batch_gallery
                            batch_result.success_images,  # batch_images_state
                            batch_result.success_texts,  # batch_texts_state
                            f"✅ {status_msg}"
                        )
                    else:
                        raise gr.Error("すべての画像生成に失敗しました")

            except Exception as e:
                progress(1.0)
                raise gr.Error(f"生成エラー: {str(e)}")

        def format_history_for_display(history: List[Dict]) -> List[Dict]:
            """Format history for chatbot display"""
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
                    if "images" in msg:
                        # Multiple images - show first one as representative
                        first_img = decode_image(msg["images"][0])
                        response_text = msg.get("content", f"{len(msg['images'])}枚の画像を生成")
                        formatted.append({
                            "role": "assistant",
                            "content": response_text,
                            "files": [first_img]
                        })
                    elif "image" in msg:
                        # Single image
                        img = decode_image(msg["image"])
                        response_text = msg.get("content", "画像を生成しました")
                        formatted.append({
                            "role": "assistant",
                            "content": response_text,
                            "files": [img]
                        })
                    else:
                        # Text only
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

                # Image indicators
                image_indicator = ""
                if "images" in msg:
                    count = msg.get("image_count", len(msg["images"]))
                    image_indicator = f"🖼️×{count} "
                elif "image" in msg:
                    image_indicator = "🖼️ "

                edited = " ✏️" if msg.get("edited") else ""

                display = f"{role_emoji} {image_indicator}{content_preview}{edited}"
                samples.append([display])

            return samples

# Individual image downloads are handled via Gallery component built-in functionality

        def on_download_batch(images: List[Image.Image], texts: List[str]):
            """Handle batch ZIP download"""
            if not images:
                return gr.update(visible=False), gr.update(visible=False), "❌ ダウンロードする画像がありません"

            try:
                print(f"🔧 DEBUG: ZIP作成中 - {len(images)}枚の画像")
                zip_path = create_batch_zip(images, texts)
                print(f"✅ DEBUG: ZIP作成完了 - {zip_path}")
                # Return the file path and make download row visible
                return (
                    zip_path,  # download_file - Pass the file path directly
                    gr.update(visible=True),  # download_row
                    "✅ ZIPファイルを作成しました。下からダウンロードできます。"
                )
            except Exception as e:
                print(f"❌ DEBUG: ZIP作成エラー - {str(e)}")
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    f"❌ ZIP作成に失敗: {str(e)}"
                )

        def on_select_history(evt: gr.SelectData, manager: ConversationManager):
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

        def on_delete(index: int, manager: ConversationManager):
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
                gr.update(visible=False),  # batch_results_group
                [],  # batch_gallery
                [],  # batch_images_state
                [],  # batch_texts_state
                gr.update(visible=False),  # download_row
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
            fn=on_generate_batch,
            inputs=[
                prompt_input,
                conversation_manager,
                batch_size_slider,
                parallel_checkbox,
                enable_batch_checkbox,
                # Combination mode inputs
                combination_mode,
                base_prompt,
                combo_a1, combo_a2, combo_a3, combo_a4,
                combo_b1, combo_b2, combo_b3, combo_b4,
                upload_image
            ],
            outputs=[
                conversation_manager,
                chatbot,
                prompt_input,
                upload_image,
                history_items,
                batch_results_group,
                batch_gallery,
                batch_images_state,
                batch_texts_state,
                status
            ]
        )

        # Also trigger generation on Enter key
        prompt_input.submit(
            fn=on_generate_batch,
            inputs=[
                prompt_input,
                conversation_manager,
                batch_size_slider,
                parallel_checkbox,
                enable_batch_checkbox,
                # Combination mode inputs
                combination_mode,
                base_prompt,
                combo_a1, combo_a2, combo_a3, combo_a4,
                combo_b1, combo_b2, combo_b3, combo_b4,
                upload_image
            ],
            outputs=[
                conversation_manager,
                chatbot,
                prompt_input,
                upload_image,
                history_items,
                batch_results_group,
                batch_gallery,
                batch_images_state,
                batch_texts_state,
                status
            ]
        )

        # Batch download events
        batch_download_btn.click(
            fn=on_download_batch,
            inputs=[batch_images_state, batch_texts_state],
            outputs=[download_file, download_row, status]
        )

        # History management events
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
                batch_results_group,
                batch_gallery,
                batch_images_state,
                batch_texts_state,
                download_row,
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


def launch_batch_app():
    """Launch the batch-enabled Gradio application"""
    settings = get_settings()
    app = create_batch_app()

    import tempfile
    temp_dir = tempfile.gettempdir()

    app.launch(
        server_name=settings.host,
        server_port=settings.port,
        share=settings.share,
        show_error=True,
        inbrowser=False,
        prevent_thread_lock=False,
        quiet=False,
        favicon_path=None,
        ssl_verify=False,
        allowed_paths=[temp_dir],
        auth=None
    )


if __name__ == "__main__":
    launch_batch_app()