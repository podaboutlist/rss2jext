import json


def populate_discs_json(
    *,
    template_file: str,
    title: str,
    author: str,
    duration: int,
    lores: list[str] = None,
) -> dict:
    with open(template_file, encoding="utf-8") as template_file:
        discs = json.load(template_file)

    discs[0]["title"] = str(title)
    discs[0]["author"] = str(author)
    discs[0]["duration"] = int(duration)

    # `lores` is optional, custom lores can be specified in the template file
    if lores:
        if len(lores < 3):
            discs[0]["lores"] = lores
        else:
            raise ValueError(f"lores array has too many items! ({len(lores)} > 2)")

    return discs
