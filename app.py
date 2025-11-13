from shiny import App, ui, render

app_ui = ui.page_navbar(
    ui.head_content(
        ui.tags.style(
            """
            .app-shell {
                position: relative;
                display: flex;
                min-height: calc(100vh - var(--bs-navbar-height, 56px));
            }
            .app-sidebar {
                position: absolute;
                top: 1rem;
                left: 1rem;
                width: 320px;
                max-width: 35vw;
                padding: 1rem;
                overflow-y: auto;
                background-color: rgba(248, 249, 250, 0.5);
                border: 1px solid #dee2e6;
                border-radius: 0.5rem;
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                backdrop-filter: blur(6px);
            }
            .app-main {
                flex: 1 1 auto;
                padding: 1.5rem;
                margin-left: 360px;
                overflow: auto;
            }
            @media (max-width: 992px) {
                .app-shell {
                    flex-direction: column;
                }
                .app-sidebar {
                    position: static;
                    width: 100%;
                    max-width: none;
                    margin: 0 0 1rem 0;
                }
                .app-main {
                    margin-left: 0;
                }
            }
            """
        )
    ),
    ui.nav_panel(
        "Dashboard",
        ui.div(
            {"class": "app-shell"},
            ui.div(
                {"class": "app-sidebar"},
                ui.h3("Sidebar"),
                ui.input_text("text_input", "Enter some text:")
            ),
            ui.div(
                {"class": "app-main"},
                ui.h3("Main Window"),
                ui.output_text("text_output")
            )
        )
    ),
    title="Raster Viewer"
)

def server(input, output, session):
    @output
    @render.text
    def text_output():
        return f"You entered: {input.text_input()}"

app = App(app_ui, server)


