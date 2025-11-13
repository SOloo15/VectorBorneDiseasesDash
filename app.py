from shiny import App, ui, render
import folium

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
                z-index: 1000;
            }
            .app-main {
                position: relative;
                flex: 1 1 auto;
                padding: 1.5rem;
                margin-left: 0;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                z-index: 0;
            }
            .app-main::after {
                content: "";
                position: absolute;
                inset: 0;
                background: rgba(255, 255, 255, 0.45);
                backdrop-filter: blur(4px);
                pointer-events: none;
                z-index: -1;
            }
            .map-container {
                flex: 1 1 auto;
                min-height: 500px;
                filter: saturate(0.8);
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
                #ui.h3("Main Window"),
                ui.div(
                    {"class": "map-container"},
                    ui.output_ui("leaflet_map")
                )
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

    @output
    @render.ui
    def leaflet_map():
        m = folium.Map(
            location=[-1.286389, 36.817223],
            zoom_start=12,
            tiles="CartoDB positron",
            width="100%",
            height=600
        )
        return ui.HTML(m._repr_html_())

app = App(app_ui, server)


