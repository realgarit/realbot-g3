# Copyright (c) 2026 realgarit
from modules.core.context import context


def get_tile_type_name(tile_type: int) -> str:
    if context.rom.is_rs:
        rse = True
        frlg = False
        emerald = False
    elif context.rom.is_emerald:
        rse = True
        frlg = False
        emerald = True
    else:
        rse = False
        frlg = True
        emerald = False

    match tile_type:
        case 0x00:
            return "Normal"
        case 0x01:
            return "Secret Base Wall"
        case 0x02:
            return "Tall Grass"
        case 0x03:
            return "Long Grass"
        case 0x06:
            return "Deep Sand"
        case 0x07:
            return "Short Grass"
        case 0x08:
            return "Cave"
        case 0x09:
            return "Long Grass South Edge"
        case 0x0A:
            return "No Running"
        case 0x0B:
            return "Indoor Encounter"
        case 0x0C:
            return "Mountain Top"
        case 0x0D:
            return "Battle Pyramid Warp" if emerald else "Secret Base Glitter Map"
        case 0x0E:
            return "Mossdeep Gym Warp"
        case 0x0F:
            return "Mount Pyre Hole"
        case 0x10:
            return "Pond Water"
        case 0x11:
            if emerald:
                return "Interior Deep Water"  # Used by interior maps; functionally the same as MB_DEEP_WATER
            elif frlg:
                return "Fast Water"
            else:
                return "Semi-Deep Water"
        case 0x12:
            return "Deep Water"
        case 0x13:
            return "Waterfall"
        case 0x14:
            return "Sootopolis Deep Water"
        case 0x15:
            return "Ocean Water"
        case 0x16:
            return "Puddle"
        case 0x17:
            return "Shallow Water"
        case 0x18:
            return "Sootopolis Deep Water (2)"
        case 0x19:
            return "Underwater Blocked Above"
        case 0x1A:
            return "Sootopolis Deep Water (3)"
        case 0x1B:
            return "Stairs Outside Abandoned Ship" if rse else "Cycling Road Water"
        case 0x1C:
            return "Shoal Cave Entrance"
        case 0x20:
            return "Ice" if rse else "Strength Button"
        case 0x21:
            return "Sand"
        case 0x22:
            return "Seaweed"
        case 0x23:
            return "Ice"
        case 0x24:
            return "Ash Grass"
        case 0x25:
            return "Footprints"
        case 0x26:
            return "Thin Ice"
        case 0x27:
            return "Cracked Ice"
        case 0x28:
            return "Hot Springs"
        case 0x29:
            return "Lavaridge Gym B1F Warp"
        case 0x2A:
            return "Seaweed No Surfacing" if rse else "Rock Stairs"
        case 0x2B:
            return "Reflection Under Bridge" if rse else "Sand Cave"
        case 0x30:
            return "Impassable East"
        case 0x31:
            return "Impassable West"
        case 0x32:
            return "Impassable North"
        case 0x33:
            return "Impassable South"
        case 0x34:
            return "Impassable North/East"
        case 0x35:
            return "Impassable North/West"
        case 0x36:
            return "Impassable South/East"
        case 0x37:
            return "Impassable South/West"
        case 0x38:
            return "Jump East"
        case 0x39:
            return "Jump West"
        case 0x3A:
            return "Jump North"
        case 0x3B:
            return "Jump South"
        case 0x3C:
            return "Jump North/East"
        case 0x3D:
            return "Jump North/West"
        case 0x3E:
            return "Jump South/East"
        case 0x3F:
            return "Jump South/West"
        case 0x40:
            return "Walk East"
        case 0x41:
            return "Walk West"
        case 0x42:
            return "Walk North"
        case 0x43:
            return "Walk South"
        case 0x44:
            return "Slide East"
        case 0x45:
            return "Slide West"
        case 0x46:
            return "Slide North"
        case 0x47:
            return "Slide South"
        case 0x48:
            return "Trick House Puzzle 8 Floor"
        case 0x50:
            return "Eastward Current"
        case 0x51:
            return "Westward Current"
        case 0x52:
            return "Northward Current"
        case 0x53:
            return "Southward Current"
        case 0x54:
            return "Spin Right"
        case 0x55:
            return "Spin Left"
        case 0x56:
            return "Spin Up"
        case 0x57:
            return "Spin Down"
        case 0x60:
            return "Non-Animated Door"
        case 0x61:
            return "Warp"
        case 0x62:
            return "Warps Door"
        case 0x63:
            return "Warp South"
        case 0x64:
            return "Warp South" if rse else "Warp"
        case 0x65:
            return "Warp North" if rse else "Warp"
        case 0x66:
            return "Warp West" if rse else "Warp"
        case 0x67:
            return "Warp East" if rse else "Warp"
        case 0x68:
            return "Warp South" if rse else "Warp"
        case 0x69:
            return "Warp North" if rse else "Warp"
        case 0x6A:
            return "Warp West" if rse else "Warp"
        case 0x6B:
            return "Warp East" if rse else "Warp"
        case 0x6C:
            return "Warp Door"
        case 0x6D:
            return "Warp Escalator North" if rse else "Plastic Mat"
        case 0x6E:
            return "Warp Escalator South"
        case 0x70:
            return "Union Room Warp"
        case 0x80:
            return "Counter"
        case 0x81:
            return "Bookshelf"
        case 0x82:
            return "Pokéblock Feeder" if rse else "Tank"
        case 0x83:
            return "Secret Base Entrance" if rse else "Node"
        case 0x84:
            return "Sign"
        case 0x85:
            return "PC"
        case 0x86:
            return "Television"
        case 0xD0:
            return "Cycling Road North"
        case 0xD1:
            return "Cycling Road South"
        case 0xE9:
            return "Trainer Hill Timer"
        case 0xEA:
            return "Sky Pillar Closed Door"
        case _:
            return "???"
