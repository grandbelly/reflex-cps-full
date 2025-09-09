"""
equipment_3d.py
==================

This module defines a simple 3D equipment monitoring page for a Reflex
(Pynecone) application.  The implementation uses Plotly to render a
rotatable 3D cube whose colour reflects the current state of one or
more sensors.  A set of example sensor definitions are loaded from
an XML file (``test2.xml``) on initialisation, and a button on the
page allows you to simulate real‑time updates of the sensor values.

To integrate this page into an existing Reflex app, import the
``equipment3d`` view (decorated with ``@rx.page``) and call
``app.add_page(equipment3d)`` from your application factory.  See
comments at the bottom of this file for a minimal example.

Note: this code depends on the ``reflex`` (Pynecone) and
``plotly`` libraries, which must be installed in your environment.  It
is intended as a starting point for building a digital twin style
dashboard; you may wish to replace the random sensor updates with
subscriptions to your real data sources (e.g. MQTT, database queries
or websockets).
"""

from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from typing import Dict, Tuple

import plotly.graph_objects as go

import reflex as rx


def create_cube_figure(sensors: Dict[str, float]) -> go.Figure:
    """Create a Plotly figure containing a coloured cube.

    The colour of the cube encodes the average of the provided sensor
    values: higher values produce a redder cube, while lower values
    produce a greener cube.  The cube is constructed from eight
    vertices and twelve triangular faces.

    Args:
        sensors: A mapping from sensor names to their current values.

    Returns:
        A Plotly Figure object representing the cube.
    """
    # Compute a normalised intensity based on the mean of sensor values.
    if sensors:
        mean_value = sum(sensors.values()) / len(sensors)
    else:
        mean_value = 0.0
    # Clamp the mean into the range [0, 1] and map to an RGB colour.
    intensity = max(0.0, min(mean_value / 100.0, 1.0))
    # Green to red gradient: low values => green, high => red.
    red = int(255 * intensity)
    green = int(255 * (1.0 - intensity))
    blue = 100  # fixed blue channel for contrast.
    colour = f"rgb({red},{green},{blue})"

    # Vertices of a unit cube.
    x = [0, 1, 1, 0, 0, 1, 1, 0]
    y = [0, 0, 1, 1, 0, 0, 1, 1]
    z = [0, 0, 0, 0, 1, 1, 1, 1]
    # Faces defined by triples of vertex indices.
    i = [0, 0, 0, 1, 1, 2, 4, 5, 6, 4, 7, 6]
    j = [1, 2, 3, 2, 3, 3, 5, 6, 7, 5, 6, 7]
    k = [3, 3, 2, 3, 2, 1, 7, 7, 4, 6, 4, 5]

    mesh = go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=i,
        j=j,
        k=k,
        color=colour,
        opacity=0.8,
        flatshading=True,
    )
    fig = go.Figure(data=[mesh])
    fig.update_layout(
        scene=dict(
            aspectmode="data",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
        ),
        margin=dict(l=0, r=0, b=0, t=0),
    )
    return fig


class Equipment3DState(rx.State):
    """State class to hold and update sensor values for the 3D page."""

    # Mapping of sensor names to their latest values.
    sensors: Dict[str, float] = {}

    async def on_load(self) -> None:
        """Initialise the list of sensors from the XML configuration.

        This method runs automatically when the page is first rendered.
        It attempts to parse the ``test2.xml`` file in the working
        directory and extract the names of all ``analog`` tags.  If
        parsing fails (for instance if the file is missing), an empty
        dictionary is used instead.  In a production system you would
        populate ``self.sensors`` from your database or an API.
        """
        try:
            tree = ET.parse("test2.xml")
            root = tree.getroot()
            tags = root.find("tags")
            analogs = tags.findall("analog") if tags is not None else []
            # Initialise all sensor values to zero.
            self.sensors = {analog.attrib.get("name", f"sensor_{idx}"): 0.0 for idx, analog in enumerate(analogs)}
        except Exception:
            # Default to two example sensors if the file cannot be parsed.
            self.sensors = {"analog_1": 0.0, "analog_2": 0.0}

    def update_sensors(self) -> None:
        """Simulate a real‑time update of sensor values.

        This method assigns random floating point numbers to each
        registered sensor.  You can replace the random values with
        readings from an MQTT subscription, database query or other
        external data source.  Once this method modifies ``self.sensors``,
        Reflex will automatically trigger a UI update.
        """
        updated = {}
        for name in self.sensors:
            # Generate a new random value between 0 and 100.
            updated[name] = random.uniform(0.0, 100.0)
        self.sensors = updated

    @rx.var
    def figure(self) -> go.Figure:
        """A computed property returning the current cube figure.

        Reflex automatically recalculates this property whenever a
        dependency (in this case ``self.sensors``) changes, and
        components referencing it will update on the client side.

        Returns:
            A Plotly Figure representing the equipment cube coloured by
            the current sensor values.
        """
        return create_cube_figure(self.sensors)


@rx.page(route="/equipment3d", title="3D Equipment Monitor")
def equipment3d() -> rx.Component:
    """Render the 3D equipment monitoring page.

    The page consists of a heading, a button to manually refresh
    (simulate) sensor values, the 3D plot itself, and a simple list
    showing the names and numeric values of each sensor.  Because the
    plot is interactive, users can rotate and zoom the cube to view it
    from any angle.  The colour of the cube updates whenever the
    sensors change.
    """
    state = Equipment3DState
    return rx.container(
        rx.heading("3D 설비 모니터링", size="lg", margin_bottom="1em"),
        rx.button("센서 값 갱신", on_click=state.update_sensors, margin_bottom="1em"),
        rx.plotly(state.figure),
        # Display sensor names and values as a vertical list.
        rx.vstack(
            rx.foreach(
                state.sensors.items(),
                lambda item: rx.text(f"{item[0]}: {item[1]:.2f}", font_size="sm")
            ),
            margin_top="1em",
        ),
        width="100%",
        align_items="center",
        padding="2em",
    )


# ---------------------------------------------------------------------------
# Example integration into a Reflex application.
#
# The following commented code shows how you might incorporate this page
# into your existing Reflex application.  Uncomment and adapt as
# necessary.
#
# import reflex as rx
#
# app = rx.App()
# # Register the new page under the "/equipment3d" route.
# app.add_page(equipment3d)
# # Optionally, specify a custom page title.
# app.compile()
