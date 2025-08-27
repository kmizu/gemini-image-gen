"""UI components for batch image generation and display"""

import gradio as gr
from typing import List, Dict, Optional, Callable, Tuple, Any
from PIL import Image

from ..utils.file_utils import create_batch_zip, save_image_with_metadata
from ..core.conversation import ConversationManager


class BatchImageMatrix:
    """Component for displaying and managing batch-generated images"""

    def __init__(self):
        self.images: List[Image.Image] = []
        self.texts: List[str] = []
        self.selected_indices: List[int] = []
        self.temp_files: List[str] = []

    def create_matrix_display(self, max_columns: int = 4) -> gr.Group:
        """
        Create a matrix display for batch images

        Args:
            max_columns: Maximum number of columns in the grid

        Returns:
            Gradio Group containing the matrix display
        """
        with gr.Group() as matrix_group:
            gr.Markdown("### 🖼️ 生成された画像")

            # Image grid container
            self.image_grid = gr.HTML(value="", visible=False)

            # Individual image displays (hidden, used for interactions)
            self.image_displays = []
            self.download_buttons = []
            self.select_buttons = []

            # Create hidden components for up to 16 images
            for i in range(16):
                with gr.Group(visible=False) as img_group:
                    img_display = gr.Image(
                        type="pil",
                        show_download_button=False,
                        interactive=False,
                        container=False
                    )
                    with gr.Row():
                        download_btn = gr.Button(
                            f"💾 DL {i+1}",
                            size="sm",
                            scale=1
                        )
                        select_btn = gr.Button(
                            f"✓ 選択 {i+1}",
                            size="sm",
                            scale=1,
                            variant="secondary"
                        )

                self.image_displays.append(img_display)
                self.download_buttons.append(download_btn)
                self.select_buttons.append(select_btn)

            # Batch controls
            with gr.Row(visible=False) as batch_controls:
                self.batch_download_btn = gr.Button(
                    "📦 全画像をZIPダウンロード",
                    variant="primary",
                    scale=2
                )
                self.clear_batch_btn = gr.Button(
                    "🗑️ クリア",
                    variant="stop",
                    scale=1
                )

            # Selection summary
            self.selection_info = gr.Markdown("", visible=False)

            # Hidden state components
            self.batch_images_state = gr.State([])
            self.batch_texts_state = gr.State([])
            self.selected_state = gr.State([])

            self.matrix_group = matrix_group
            self.batch_controls = batch_controls

        return matrix_group

    def update_display(
        self,
        images: List[Image.Image],
        texts: List[str],
        max_columns: int = 4
    ) -> Tuple[gr.HTML, gr.Group, List[gr.Image], List[gr.Button], gr.Markdown, gr.State, gr.State]:
        """
        Update the matrix display with new images

        Args:
            images: List of PIL Images
            texts: List of text descriptions
            max_columns: Maximum columns in grid

        Returns:
            Updated components
        """
        self.images = images[:]
        self.texts = texts[:]
        self.selected_indices = []

        if not images:
            return (
                gr.update(value="", visible=False),
                gr.update(visible=False),
                [gr.update(visible=False) for _ in self.image_displays],
                [gr.update(visible=False) for _ in self.download_buttons],
                gr.update(value="", visible=False),
                gr.State([]),
                gr.State([])
            )

        # Create HTML grid
        num_images = len(images)
        num_columns = min(max_columns, num_images)
        num_rows = (num_images + num_columns - 1) // num_columns

        html_grid = self._create_html_grid(images, texts, num_columns)

        # Update individual image displays
        image_updates = []
        button_updates = []

        for i in range(len(self.image_displays)):
            if i < num_images:
                image_updates.append(gr.update(value=images[i], visible=True))
                button_updates.append(gr.update(visible=True))
            else:
                image_updates.append(gr.update(visible=False))
                button_updates.append(gr.update(visible=False))

        selection_info = f"生成された画像: {num_images}枚"

        return (
            gr.update(value=html_grid, visible=True),
            gr.update(visible=True),
            image_updates,
            button_updates,
            gr.update(value=selection_info, visible=True),
            gr.State(images),
            gr.State(texts)
        )

    def _create_html_grid(
        self,
        images: List[Image.Image],
        texts: List[str],
        num_columns: int
    ) -> str:
        """Create HTML grid for image display"""
        html = '''
        <div style="display: grid; grid-template-columns: repeat(%d, 1fr); gap: 10px; margin: 10px 0;">
        ''' % num_columns

        for i, (image, text) in enumerate(zip(images, texts)):
            # Convert image to base64 for display
            import io
            import base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            # Truncate text for display
            display_text = text[:50] + "..." if len(text) > 50 else text

            html += f'''
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 8px; text-align: center; background: white;">
                <img src="data:image/png;base64,{img_base64}"
                     style="width: 100%; height: 200px; object-fit: cover; border-radius: 4px; margin-bottom: 8px;"
                     alt="Generated Image {i+1}">
                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">{display_text}</div>
                <div style="font-size: 11px; color: #999;">画像 {i+1}</div>
            </div>
            '''

        html += '</div>'
        return html

    def download_single_image(self, index: int, images: List[Image.Image], texts: List[str]) -> Optional[str]:
        """
        Download a single image

        Args:
            index: Index of image to download
            images: List of images
            texts: List of texts

        Returns:
            Path to saved file or None
        """
        if not (0 <= index < len(images)):
            return None

        try:
            image = images[index]
            text = texts[index] if index < len(texts) else ""
            return save_image_with_metadata(image, text)
        except Exception as e:
            print(f"Download error: {e}")
            return None

    def download_batch_zip(self, images: List[Image.Image], texts: List[str]) -> Optional[str]:
        """
        Create and download ZIP file with all images

        Args:
            images: List of images
            texts: List of texts

        Returns:
            Path to ZIP file or None
        """
        if not images:
            return None

        try:
            return create_batch_zip(images, texts)
        except Exception as e:
            print(f"ZIP creation error: {e}")
            return None

    def toggle_selection(self, index: int, current_selected: List[int]) -> Tuple[List[int], str]:
        """
        Toggle selection of an image

        Args:
            index: Index of image to toggle
            current_selected: Currently selected indices

        Returns:
            Updated selection list and info text
        """
        new_selected = current_selected[:]

        if index in new_selected:
            new_selected.remove(index)
        else:
            new_selected.append(index)

        if new_selected:
            info = f"選択された画像: {len(new_selected)}枚 (インデックス: {sorted(new_selected)})"
        else:
            info = "選択された画像: なし"

        return new_selected, info

    def clear_batch(self) -> Tuple[gr.HTML, gr.Group, List[gr.Image], List[gr.Button], gr.Markdown, gr.State, gr.State]:
        """Clear all batch data"""
        self.images = []
        self.texts = []
        self.selected_indices = []

        return (
            gr.update(value="", visible=False),
            gr.update(visible=False),
            [gr.update(visible=False) for _ in self.image_displays],
            [gr.update(visible=False) for _ in self.download_buttons],
            gr.update(value="", visible=False),
            gr.State([]),
            gr.State([])
        )


class BatchGenerationSettings:
    """Component for batch generation settings"""

    def __init__(self, default_batch_size: int = 4, max_batch_size: int = 8):
        self.default_batch_size = default_batch_size
        self.max_batch_size = max_batch_size

    def create_settings_panel(self) -> gr.Group:
        """Create settings panel for batch generation"""
        with gr.Group() as settings_group:
            gr.Markdown("### ⚙️ バッチ生成設定")

            with gr.Row():
                self.batch_size_slider = gr.Slider(
                    minimum=1,
                    maximum=self.max_batch_size,
                    value=self.default_batch_size,
                    step=1,
                    label="生成枚数",
                    info=f"1-{self.max_batch_size}枚"
                )

                self.parallel_checkbox = gr.Checkbox(
                    label="並列生成",
                    value=True,
                    info="高速化（推奨）"
                )

            with gr.Row():
                self.enable_batch_checkbox = gr.Checkbox(
                    label="バッチ生成を有効化",
                    value=False,
                    info="チェックすると複数枚生成"
                )

        return settings_group

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        return {
            "batch_size": self.batch_size_slider.value,
            "use_parallel": self.parallel_checkbox.value,
            "enable_batch": self.enable_batch_checkbox.value
        }