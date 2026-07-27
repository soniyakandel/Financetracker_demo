import os

from app import create_app

app = create_app()


def _serve():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    if app.debug:
        app.run(host=host, port=port)
        return

    from waitress import serve

    threads = int(os.getenv("WEB_THREADS", "8"))
    app.logger.info("Serving on http://%s:%s with %s threads", host, port, threads)
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        ident=None,
    )


if __name__ == "__main__":
    _serve()
