from tender_system.api import create_app


app = create_app()


if __name__ == "__main__":
    import importlib

    uvicorn = importlib.import_module("uvicorn")
    uvicorn.run(app, host="127.0.0.1", port=8000)
