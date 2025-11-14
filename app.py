from datetime import date, timedelta
from io import BytesIO
import base64
import os
import folium
import numpy as np
import rasterio
from matplotlib import cm, pyplot as plt
from rasterio.warp import transform_bounds
from shiny import App, ui, render, reactive

GRADIENT_COLORS = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]
GRADIENT_CSS = ", ".join(
    f"{color} {int(i / (len(GRADIENT_COLORS) - 1) * 100)}%"
    for i, color in enumerate(GRADIENT_COLORS)
)

mosquito_variables = {
    "Egg Count": "mosquito_Egg_count_",
    "Entomological Inoculation Rate": "mosquito_EIR_",
    "Female Adult Mosquito Count": "mosquito_Female_Adults_count_",
}
climatic_variables = {
    "Rainfal": "mosquito_Rainfall_",
    "Temperature": "mosquito_Temperature_",
}
variable_options = {**mosquito_variables, **climatic_variables}

date_min = date(2021, 1, 1)
date_max = date(2021, 3, 31)

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
            .navbar-info-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 1.15rem;
                margin-left: 1rem;
                color: var(--bs-navbar-color, #495057);
                text-decoration: none;
            }
            .navbar-info-icon:hover {
                color: var(--bs-primary, #0d6efd);
            }
            """
        )
    ),
    ui.nav_spacer(),
    ui.nav_panel(
        "Mosquito",
        ui.div(
            {"class": "app-shell"},
            ui.div(
                {"class": "app-sidebar"},
                ui.h3("Mosquito variables"),
                ui.input_radio_buttons(
                    "selected_variable",
                    "Select variable:",
                    choices=list(mosquito_variables.keys()),
                    selected=list(mosquito_variables.keys())[0],
                ),
                ui.input_slider(
                    "selected_date",
                    "Select date:",
                    min=date_min,
                    max=date_max,
                    value=date_min,
                    step=timedelta(days=1),
                ),
                ui.div(
                    ui.output_ui("legend_panel"),
                    style="margin-top:1.5rem;",
                ),
            ),
            ui.div(
                {"class": "app-main"},
                ui.div(
                    {"class": "map-container"},
                    ui.output_ui("leaflet_map"),
                ),
            ),
        ),
    ),
    ui.nav_panel(
        "Climate",
        ui.div(
            {"class": "app-shell"},
            ui.div(
                {"class": "app-sidebar"},
                ui.h3("Climate variables"),
                ui.input_radio_buttons(
                    "selected_climate_variable",
                    "Select variable:",
                    choices=list(climatic_variables.keys()),
                    selected=list(climatic_variables.keys())[0],
                ),
                ui.input_slider(
                    "selected_climate_date",
                    "Select date:",
                    min=date_min,
                    max=date_max,
                    value=date_min,
                    step=timedelta(days=1),
                ),
                ui.div(
                    ui.output_ui("climate_legend_panel"),
                    style="margin-top:1.5rem;",
                ),
            ),
            ui.div(
                {"class": "app-main"},
                ui.div(
                    {"class": "map-container"},
                    ui.output_ui("climate_map"),
                ),
            ),
        ),
    ),
    ui.nav_panel(
        "Computation"
    ),
    ui.nav_spacer(),
    ui.nav_control(
        ui.input_action_button(
            "show_info",
            "ⓘ",
            class_="navbar-info-icon",
            title="Data info"
        )
    ),
    title="ARBO WATCH Network",
)

def server(input, output, session):
    def show_about_modal():
        ui.modal_show(
            ui.modal(
                ui.h3("About"),
                ui.p(
                    "Modelling dengue and chikungunya transmission patterns for improved "
                    "public health decision-making in the Horn of Africa"
                ),
                ui.p(
                    "The dashboard serves as a platform for running and displaying results "
                    "of dengue and Chikungunya transmission models. The models are implemented "
                    "on a grid of 20km and it couples the mosquito population dynamics "
                    "sub-model and virus transmission sub-model. The development rates of "
                    "mosquitoes are dependent on rainfall and temperature. The platform can "
                    "be used for forecasting the risk of these diseases."
                ),
                ui.p("Developed by: ILRI"),
                ui.p("Version: 1.0"),
                ui.strong("Contact: info@example.com"),
                easy_close=True,
                footer=ui.modal_button("Close"),
            )
        )

    session.on_flush(lambda: show_about_modal(), once=True)

    def build_overlay(prefix_map, variable_name, selected_date):
        if not variable_name or not selected_date:
            return None
        prefix = prefix_map.get(variable_name, "")
        if not prefix:
            return None
        date_str = selected_date.strftime("%Y%m%d")
        tiff_path = os.path.join("rasters_by_date", f"{prefix}{date_str}.tif")
        if not os.path.exists(tiff_path):
            return None
        with rasterio.open(tiff_path) as src:
            band = src.read(1, masked=True).astype(float)
            bounds_src = src.bounds
            crs = src.crs
        if crs is not None and crs.to_string() != "EPSG:4326":
            left, bottom, right, top = transform_bounds(crs, "EPSG:4326", *bounds_src)
        else:
            left, bottom, right, top = (
                bounds_src.left,
                bounds_src.bottom,
                bounds_src.right,
                bounds_src.top,
            )
        masked_band = np.ma.masked_invalid(band)
        if masked_band.count() == 0:
            return None
        data = masked_band.filled(np.nan)
        vmin = float(np.nanmin(data))
        vmax = float(np.nanmax(data))
        norm = np.zeros_like(data)
        if not np.isclose(vmin, vmax):
            norm = (data - vmin) / (vmax - vmin)
        norm = np.ma.array(norm, mask=~np.isfinite(data))
        cmap = cm.get_cmap("viridis").copy()
        cmap.set_bad(alpha=0)
        buf = BytesIO()
        plt.imsave(buf, norm, cmap=cmap, format="png")
        buf.seek(0)
        image_uri = f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"
        return {
            "image_uri": image_uri,
            "bounds": ((bottom, left), (top, right)),
            "legend": {
                "label": variable_name,
                "date_label": selected_date.strftime("%d %b %Y"),
                "vmin": vmin,
                "vmax": vmax,
            },
        }

    @reactive.calc
    def raster_overlay_mosquito():
        return build_overlay(
            mosquito_variables,
            input.selected_variable(),
            input.selected_date(),
        )

    @reactive.calc
    def raster_overlay_climate():
        return build_overlay(
            climatic_variables,
            input.selected_climate_variable(),
            input.selected_climate_date(),
        )

    def render_map(overlay):
        m = folium.Map(
            location=[-1.286389, 36.817223],
            zoom_start=5,
            tiles="CartoDB positron",
            width="100%",
            height=700,
        )
        if overlay is not None:
            (bottom, left), (top, right) = overlay["bounds"]
            folium.raster_layers.ImageOverlay(
                image=overlay["image_uri"],
                bounds=[[bottom, left], [top, right]],
                opacity=0.7,
            ).add_to(m)
        folium.LayerControl().add_to(m)
        return ui.HTML(m._repr_html_())

    def render_legend(overlay):
        if overlay is None:
            return ui.HTML(
                """
                <div style="font-size:12px;color:#6c757d;">
                    Select a variable and date to view the legend.
                </div>
                """
            )
        legend = overlay["legend"]
        return ui.HTML(
            f"""
            <div style="
                background: rgba(248,249,250,0.85);
                padding: 12px 14px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.15);
                font-size: 13px;
                line-height: 1.4;
            ">
                <div style="font-weight: 600; margin-bottom: 6px;">{legend['label']}</div>
                <div style="margin-bottom: 10px;">Date: {legend['date_label']}</div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="
                        width: 100%;
                        height: 16px;
                        background-image: linear-gradient(90deg, {GRADIENT_CSS});
                        border-radius: 4px;
                        border: 1px solid rgba(0,0,0,0.15);
                    "></div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 11px; font-weight: 500;">{legend['vmin']:.2f}</span>
                        <span style="font-size: 11px; font-weight: 500;">{legend['vmax']:.2f}</span>
                    </div>
                </div>
            </div>
            """
        )

    @output
    @render.ui
    def leaflet_map():
        return render_map(raster_overlay_mosquito())

    @output
    @render.ui
    def legend_panel():
        return render_legend(raster_overlay_mosquito())

    @output
    @render.ui
    def climate_map():
        return render_map(raster_overlay_climate())

    @output
    @render.ui
    def climate_legend_panel():
        return render_legend(raster_overlay_climate())

    @reactive.effect
    @reactive.event(input.show_info)
    def _show_about():
        show_about_modal()
app = App(app_ui, server)


