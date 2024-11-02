import argparse
import os

from jinja2 import Environment, PackageLoader, select_autoescape


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Python file with boilerplate code for a data service."
    )
    parser.add_argument(
        "filename", type=str, help="The name of the Python file to create."
    )
    parser.add_argument(
        "--data-item",
        action="store_true",
        help="Include BaseDataItem in the generated code.",
    )
    parser.add_argument(
        "--service-config",
        action="store_true",
        help="Include ServiceConfig in the generated code.",
    )
    parser.add_argument(
        "--proxy-config", action="store_true", help="Import ProxyConfig."
    )
    parser.add_argument(
        "--async-service",
        action="store_true",
        help="Use AsyncDataService and make the main function async.",
    )
    parser.add_argument(
        "--client",
        help="The name of the client to use. Default is HttpXClient.",
        choices=["httpx", "playwright"],
        default="httpx",
    )

    args = parser.parse_args()

    filename = args.filename
    if not filename.endswith(".py"):
        filename = f"{filename}.py"
    script_name = filename.split(".")[0]
    use_httpx_client = args.client == "httpx"
    use_playwright_client = args.client == "playwright"
    use_async_data_service = args.async_service
    use_data_service = not use_async_data_service

    env = Environment(
        loader=PackageLoader("dataservice", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("template.py.j2")

    content = template.render(
        script_name=script_name,
        use_base_data_item=args.data_item,
        use_service_config=args.service_config,
        use_httpx_client=use_httpx_client,
        use_playwright_client=use_playwright_client,
        use_data_service=use_data_service,
        use_async_data_service=use_async_data_service,
    )

    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, "w") as f:
        f.write(content)

    print(f"File '{filename}' created with boilerplate code.")


if __name__ == "__main__":
    main()
