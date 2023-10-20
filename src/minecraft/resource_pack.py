"""Validate and build resource packs for Minecraft."""

import json
import os
import shutil

import png

VALID_PACK_VERSIONS = [
    8,  # 1.18 - 1.18.2
    9,  # 1.19 - 1.19.2
    12,  # 1.19.3
    15,  # 1.20-1.20.1
    18,  # 1.20.2
]


class ResourcePack:

    """Manage metadata and build resource packs for Minecraft."""

    __pack_format: int = None
    __pack_description: str = None
    __data_dir: str = None
    __output_file: str = None

    def __init__(
        self,
        *,
        pack_version: int,
        pack_description: str,
        data_dir: str,
        output_file: str,
    ) -> None:
        """Provide pack metadata for building."""
        self.__pack_format = self.validate_pack_version(pack_version)
        self.__pack_description = pack_description
        self.__data_dir = data_dir
        self.__output_file = output_file

        self.validate_pack_icon()

    def __populate_mcmeta(self, template: dict) -> dict:
        output = template

        output["pack"]["pack_format"] = self.__pack_format
        output["pack"]["description"] = self.__pack_description

        return output

    def __clean_tmp(self):
        shutil.rmtree(os.path.join(self.__data_dir, "tmp", "resourcepack"))

    def validate_pack_icon(self) -> str | None:
        """Check if pack.png exists.

        If it isn't a 64x64px PNG, raise an exception.
        """
        icon_path = os.path.join(self.__data_dir, "pack.png")

        if not os.path.exists(icon_path):
            return None

        reader = png.Reader(filename=icon_path)
        width, height, *_ = reader.read()

        if not width == height == 64:
            raise RuntimeError(f"{icon_path} is not a 64x64px PNG!")

        return icon_path

    def validate_pack_version(self, pack_version: int) -> int:
        """Ensure pack_version matches the spec set by Minecraft.

        For more info, see https://minecraft.fandom.com/wiki/Pack_format#Resources.
        """
        pv = int(pack_version)

        if pv not in VALID_PACK_VERSIONS:
            raise ValueError(f"pack_version is not one of {VALID_PACK_VERSIONS}")

        return pv

    def build(self, *, basename: str, verbose=False):
        """Create resource pack using template files."""
        # Clean up any previous data to prevent FileExistsError
        self.__clean_tmp()

        tmp_dir = os.path.join(self.__data_dir, "tmp")
        build_dir = os.path.join(tmp_dir, "resourcepack")
        template_dir = os.path.join(self.__data_dir, "templates", "resourcepack")

        episode_ogg = os.path.join(tmp_dir, f"{basename}.ogg")
        out_zip = os.path.join(
            self.__data_dir, "out", f"{self.__output_file}_{self.__pack_format}"
        )

        # data/templates/resourcepack -> data/tmp/resourcepack
        shutil.copytree(template_dir, build_dir)

        # 1) Populate mcmeta template
        with open(
            os.path.join(template_dir, "pack.mcmeta"), encoding="utf-8"
        ) as mcmeta_template_file:
            mcmeta = self.__populate_mcmeta(json.load(mcmeta_template_file))

        with open(
            os.path.join(build_dir, "pack.mcmeta"), "w", encoding="utf-8"
        ) as mcmeta_file:
            json.dump(mcmeta, mcmeta_file, allow_nan=False)

        # 2) Copy .ogg file
        shutil.copyfile(
            episode_ogg,
            os.path.join(
                build_dir,
                "assets",
                "minecraft",
                "sounds",
                "records",
                "latestpodepisode.ogg",
            ),
        )

        # 3) zip output
        return shutil.make_archive(out_zip, "zip", root_dir=build_dir, verbose=verbose)
