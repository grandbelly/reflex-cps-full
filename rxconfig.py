import reflex as rx


config = rx.Config(
    app_name="ksys_app",
    # External React packages are inferred per Component.create calls; keep list empty to avoid resolver warnings.
    frontend_packages=[],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    frontend_port=13000,
    backend_port=13001,
)
