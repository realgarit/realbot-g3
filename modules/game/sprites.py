# Copyright (c) 2026 realgarit
from pathlib import Path

import PIL.Image
import PIL.ImageDraw

from modules.core.files import make_string_safe_for_file_name
from modules.pokemon.pokemon import Pokemon, Species
from modules.core.runtime import get_sprites_path, get_data_path


def crop_sprite_square(path: Path) -> PIL.Image:
    """
    Crops a sprite to the smallest possible size while keeping the image square.
    :param path: Path to the sprite
    :return: Cropped image
    """
    image: PIL.Image = PIL.Image.open(path)
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    bbox = list(image.getbbox())
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    # Make sure the image is square (width == height)
    if bbox_width - bbox_height:
        # Wider than high
        missing_height = bbox_width - bbox_height
        bbox[1] -= missing_height // 2
        bbox[3] += missing_height // 2 + (missing_height % 2)
    else:
        # Higher than wide (or equal sizes)
        missing_width = bbox_height - bbox_width
        bbox[0] -= missing_width // 2
        bbox[2] += missing_width // 2 + (missing_width % 2)

    # Make sure we didn't move the bounding box out of scope
    if bbox[0] < 0:
        bbox[2] -= bbox[0]
        bbox[0] = 0
    if bbox[1] < 0:
        bbox[3] -= bbox[1]
        bbox[1] = 0
    if bbox[2] > image.width:
        bbox[0] -= bbox[2] - image.width
        bbox[2] = image.width
    if bbox[3] > image.height:
        bbox[1] -= bbox[3] - image.height
        bbox[3] = image.height

    return image.crop(bbox)


def generate_placeholder_image(width: int, height: int) -> PIL.Image:
    """
    Create a black placeholder image with the custom logo in the middle.
    :param width: Image width
    :param height: Image height
    :return: The generated image
    """
    placeholder = PIL.Image.new(mode="RGBA", size=(width, height))
    draw = PIL.ImageDraw.Draw(placeholder)

    # Black background
    draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill="#000000FF")

    # Paste the logo on top
    logo_path = get_data_path() / "logo.png"
    if not logo_path.exists():
        return placeholder

    sprite = PIL.Image.open(logo_path)
    if sprite.mode != "RGBA":
        sprite = sprite.convert("RGBA")
    sprite_position = (placeholder.width // 2 - sprite.width // 2, placeholder.height // 2 - sprite.height // 2)
    placeholder.paste(sprite, sprite_position, sprite)

    return placeholder


def _get_pokemon_sprite_path(pokemon_or_species: Pokemon | Species, sprite_directory: str) -> Path:
    if isinstance(pokemon_or_species, Pokemon):
        species = pokemon_or_species.species
        if species.name == "Unown":
            file_name = f"Unown ({pokemon_or_species.unown_letter})"
        else:
            file_name = species.name
    elif pokemon_or_species.name == "Unown":
        # R for RealBot!
        file_name = "Unown (R)"
    else:
        file_name = pokemon_or_species.name

    return get_sprites_path() / "pokemon" / sprite_directory / f"{make_string_safe_for_file_name(file_name)}.png"


def get_regular_sprite(pokemon_or_species: Pokemon | Species) -> Path:
    return _get_pokemon_sprite_path(pokemon_or_species, sprite_directory="normal")


def get_shiny_sprite(pokemon_or_species: Pokemon | Species) -> Path:
    return _get_pokemon_sprite_path(pokemon_or_species, sprite_directory="shiny")


def get_anti_shiny_sprite(pokemon_or_species: Pokemon | Species) -> Path:
    return _get_pokemon_sprite_path(pokemon_or_species, sprite_directory="anti-shiny")


def get_sprite(pokemon: Pokemon) -> Path:
    if pokemon.is_shiny:
        return get_shiny_sprite(pokemon)
    elif pokemon.is_anti_shiny:
        return get_anti_shiny_sprite(pokemon)
    else:
        return get_regular_sprite(pokemon)
