import os
import time
import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN")
)

# -----------------------------
# Models
# -----------------------------
MODELS = {
    "Qwen 3.6 35B":
        "Qwen/Qwen3.6-35B-A3B:featherless-ai",

    "Llama 3.1 70B":
        "meta-llama/Llama-3.1-70B-Instruct:featherless-ai",

    "Gemma 3 12B":
        "google/gemma-3-12b-it:featherless-ai"
}


# -----------------------------
# Query Model
# -----------------------------
def get_response(model_id, prompt, max_tokens, temperature):

    start = time.time()

    try:

        # Qwen needs more room because it spends
        # tokens on reasoning before answering
        actual_max_tokens = (
            1000
            if "Qwen" in model_id
            else max_tokens
        )

        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=actual_max_tokens,
            temperature=temperature
        )

        choice = response.choices[0]

        # Normal answer
        answer = choice.message.content

        # Qwen fallback
        if not answer:

            reasoning = getattr(
                choice.message,
                "reasoning",
                None
            )

            if reasoning:
                answer = (
                    "[Reasoning Output]\n\n"
                    + reasoning
                )

        # Final fallback
        if not answer:
            answer = (
                "[No response returned]\n\n"
                f"Finish Reason: {choice.finish_reason}"
            )

        elapsed = round(
            time.time() - start,
            2
        )

        words = len(answer.split())

        stats = (
            f"Response Time : {elapsed} sec\n"
            f"Word Count    : {words}"
        )

        return answer, stats

    except Exception as e:

        return (
            f"ERROR:\n{str(e)}",
            "N/A"
        )


# -----------------------------
# Compare Models
# -----------------------------
def compare_models(prompt, max_tokens, temperature):

    qwen_answer, qwen_stats = get_response(
        MODELS["Qwen 3.6 35B"],
        prompt,
        max_tokens,
        temperature
    )

    llama_answer, llama_stats = get_response(
        MODELS["Llama 3.1 70B"],
        prompt,
        max_tokens,
        temperature
    )

    gemma_answer, gemma_stats = get_response(
        MODELS["Gemma 3 12B"],
        prompt,
        max_tokens,
        temperature
    )

    return (
        qwen_answer,
        qwen_stats,
        llama_answer,
        llama_stats,
        gemma_answer,
        gemma_stats
    )


# -----------------------------
# UI
# -----------------------------
with gr.Blocks(
    title="LLM Comparison Dashboard"
) as demo:

    gr.Markdown(
        """
# 🤖 LLM Comparison Dashboard

Compare responses from:

- Qwen 3.6 35B
- Llama 3.1 70B
- Gemma 3 12B

Powered by Hugging Face Router API
"""
    )

    prompt = gr.Textbox(
        lines=5,
        label="Enter Prompt",
        placeholder="Explain Machine Learning in simple terms..."
    )

    with gr.Row():

        max_tokens = gr.Slider(
            minimum=50,
            maximum=1000,
            value=300,
            step=50,
            label="Max Tokens"
        )

        temperature = gr.Slider(
            minimum=0.0,
            maximum=2.0,
            value=0.7,
            step=0.1,
            label="Temperature"
        )

    compare_btn = gr.Button(
        "Compare Models"
    )

    with gr.Row():

        # Qwen
        with gr.Column():

            gr.Markdown(
                "## Qwen 3.6 35B"
            )

            qwen_output = gr.Textbox(
                lines=18,
                label="Response"
            )

            qwen_stats = gr.Textbox(
                lines=2,
                label="Statistics"
            )

        # Llama
        with gr.Column():

            gr.Markdown(
                "## Llama 3.1 70B"
            )

            llama_output = gr.Textbox(
                lines=18,
                label="Response"
            )

            llama_stats = gr.Textbox(
                lines=2,
                label="Statistics"
            )

        # Gemma
        with gr.Column():

            gr.Markdown(
                "## Gemma 3 12B"
            )

            gemma_output = gr.Textbox(
                lines=18,
                label="Response"
            )

            gemma_stats = gr.Textbox(
                lines=2,
                label="Statistics"
            )

    compare_btn.click(
        fn=compare_models,
        inputs=[
            prompt,
            max_tokens,
            temperature
        ],
        outputs=[
            qwen_output,
            qwen_stats,
            llama_output,
            llama_stats,
            gemma_output,
            gemma_stats
        ]
    )

demo.launch()