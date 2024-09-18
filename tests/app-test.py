import gradio as gr

def toggle_visibility(show_tab1):
    return gr.update(visible=show_tab1), gr.update(visible=not show_tab1)

with gr.Blocks() as demo:
    with gr.Row():
        btn1 = gr.Button("Show Tab 1")
        btn2 = gr.Button("Show Tab 2")
    
    with gr.Row():
        with gr.Column(visible=True) as tab1:
            gr.Markdown("This is the content of Tab 1")
        with gr.Column(visible=False) as tab2:
            gr.Markdown("This is the content of Tab 2")
    
    # Remove the hidden checkbox inputs
    btn1.click(lambda: toggle_visibility(True), outputs=[tab1, tab2])
    btn2.click(lambda: toggle_visibility(False), outputs=[tab1, tab2])

if __name__ == "__main__":
    demo.launch()