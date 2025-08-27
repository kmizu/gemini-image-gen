"""Prompt combination utilities"""

from typing import List, Tuple, Optional
import itertools


def generate_prompt_combinations(
    base_prompt: str,
    combo_a_list: List[str],
    combo_b_list: List[str]
) -> List[Tuple[str, str]]:
    """
    Generate all combinations of prompts from two lists

    Args:
        base_prompt: Base prompt text
        combo_a_list: List of A elements (4 items)
        combo_b_list: List of B elements (4 items)

    Returns:
        List of (combined_prompt, description) tuples
    """
    combinations = []

    # Filter out empty strings
    a_elements = [a.strip() for a in combo_a_list if a.strip()]
    b_elements = [b.strip() for b in combo_b_list if b.strip()]

    if not a_elements or not b_elements:
        return combinations

    # Generate all combinations
    for i, a_element in enumerate(a_elements):
        for j, b_element in enumerate(b_elements):
            # Create combined prompt
            if base_prompt.strip():
                combined_prompt = f"{base_prompt.strip()}, {a_element}, {b_element}"
            else:
                combined_prompt = f"{a_element}, {b_element}"

            # Create description for metadata
            description = f"A{i+1}×B{j+1}: {a_element} × {b_element}"

            combinations.append((combined_prompt, description))

    return combinations


def validate_combination_inputs(
    base_prompt: str,
    combo_a_list: List[str],
    combo_b_list: List[str]
) -> Tuple[bool, str]:
    """
    Validate combination inputs

    Returns:
        (is_valid, error_message)
    """
    # Filter out empty strings
    a_elements = [a.strip() for a in combo_a_list if a.strip()]
    b_elements = [b.strip() for b in combo_b_list if b.strip()]

    if len(a_elements) < 2:
        return False, "組み合わせ要素Aは最低2つ入力してください"

    if len(b_elements) < 2:
        return False, "組み合わせ要素Bは最低2つ入力してください"

    if len(a_elements) > 4:
        return False, "組み合わせ要素Aは最大4つまでです"

    if len(b_elements) > 4:
        return False, "組み合わせ要素Bは最大4つまでです"

    return True, ""


def create_combination_summary(
    base_prompt: str,
    combo_a_list: List[str],
    combo_b_list: List[str]
) -> str:
    """
    Create a summary of the combination setup
    """
    a_elements = [a.strip() for a in combo_a_list if a.strip()]
    b_elements = [b.strip() for b in combo_b_list if b.strip()]

    total_combinations = len(a_elements) * len(b_elements)

    summary = f"**組み合わせ設定:**\n"
    summary += f"- ベース: {base_prompt or '(なし)'}\n"
    summary += f"- 要素A: {len(a_elements)}個 ({', '.join(a_elements)})\n"
    summary += f"- 要素B: {len(b_elements)}個 ({', '.join(b_elements)})\n"
    summary += f"- **合計: {total_combinations}通りの組み合わせ**"

    return summary