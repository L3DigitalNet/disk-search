import asyncio
import logging
import os


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hw_radar.settings")
    import django

    django.setup()

    from hw_radar.poller.service import run

    asyncio.run(run())


if __name__ == "__main__":
    main()
