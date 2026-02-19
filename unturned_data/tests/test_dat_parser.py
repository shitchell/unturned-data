"""
Tests for the generic .dat file parser.

Covers: flat key-value, comments, BOM handling, blank lines,
nested blocks (arrays, objects, mixed), and real fixture files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from unturned_data.dat_parser import parse_dat, parse_dat_file, parse_asset_file

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# TestFlatKeyValue
# ---------------------------------------------------------------------------
class TestFlatKeyValue:
    """Key-value parsing for simple flat lines."""

    def test_string_value(self):
        result = parse_dat("Type Food")
        assert result["Type"] == "Food"

    def test_int_value(self):
        result = parse_dat("ID 13")
        assert result["ID"] == 13
        assert isinstance(result["ID"], int)

    def test_float_value(self):
        result = parse_dat("Strength 1.5")
        assert result["Strength"] == 1.5
        assert isinstance(result["Strength"], float)

    def test_negative_float(self):
        result = parse_dat("Recoil_Min_X -0.5")
        assert result["Recoil_Min_X"] == -0.5
        assert isinstance(result["Recoil_Min_X"], float)

    def test_bool_true(self):
        result = parse_dat("IsColliderSteered true")
        assert result["IsColliderSteered"] is True

    def test_bool_false(self):
        result = parse_dat("Has_Clip_Prefab false")
        assert result["Has_Clip_Prefab"] is False

    def test_bare_flag(self):
        result = parse_dat("Semi")
        assert result["Semi"] is True

    def test_multiple_flags(self):
        text = "Safety\nSemi\nAuto"
        result = parse_dat(text)
        assert result["Safety"] is True
        assert result["Semi"] is True
        assert result["Auto"] is True

    def test_quoted_string(self):
        result = parse_dat('Bleeding_Modifier "Heal"')
        assert result["Bleeding_Modifier"] == "Heal"

    def test_unquoted_guid(self):
        result = parse_dat("GUID 78fefdd23def4ab6ac8301adfcc3b2d4")
        assert result["GUID"] == "78fefdd23def4ab6ac8301adfcc3b2d4"

    def test_path_value(self):
        result = parse_dat("ConsumeAudioClip Sounds/EatCrunchy.mp3")
        assert result["ConsumeAudioClip"] == "Sounds/EatCrunchy.mp3"

    def test_multi_word_unquoted_value(self):
        # After the first space, the rest is value -- even if multi-word
        result = parse_dat("Name Repair Target")
        assert result["Name"] == "Repair Target"

    def test_quoted_value_with_spaces(self):
        result = parse_dat('OutputItems "21ede8ebffb14c5580e8c7ad149e335e x 3"')
        assert result["OutputItems"] == "21ede8ebffb14c5580e8c7ad149e335e x 3"


# ---------------------------------------------------------------------------
# TestComments
# ---------------------------------------------------------------------------
class TestComments:
    """Comment stripping."""

    def test_inline_comment(self):
        result = parse_dat('CategoryTag "732ee6ffeb18418985cf4f9fde33dd11" // Repair')
        assert result["CategoryTag"] == "732ee6ffeb18418985cf4f9fde33dd11"

    def test_comment_not_stripping_inside_quotes(self):
        # The // inside the quotes should NOT be treated as comment
        result = parse_dat('Path "https://example.com/foo"')
        assert result["Path"] == "https://example.com/foo"

    def test_path_with_single_slash_not_comment(self):
        result = parse_dat("ConsumeAudioClip Sounds/EatCrunchy.mp3")
        assert result["ConsumeAudioClip"] == "Sounds/EatCrunchy.mp3"

    def test_full_line_comment(self):
        text = "// This is a comment\nType Food"
        result = parse_dat(text)
        assert "Type" in result
        assert result["Type"] == "Food"
        # Should not have any comment key
        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestBOM
# ---------------------------------------------------------------------------
class TestBOM:
    """UTF-8 BOM handling."""

    def test_bom_at_start(self):
        text = "\ufeffType Food\nID 13"
        result = parse_dat(text)
        assert result["Type"] == "Food"
        assert result["ID"] == 13

    def test_no_bom(self):
        text = "Type Food\nID 13"
        result = parse_dat(text)
        assert result["Type"] == "Food"
        assert result["ID"] == 13


# ---------------------------------------------------------------------------
# TestBlankLines
# ---------------------------------------------------------------------------
class TestBlankLines:
    """Blank lines between keys."""

    def test_blank_lines_between_keys(self):
        text = "Type Food\n\n\nID 13\n\nHealth 10"
        result = parse_dat(text)
        assert result["Type"] == "Food"
        assert result["ID"] == 13
        assert result["Health"] == 10


# ---------------------------------------------------------------------------
# TestNestedBlocks
# ---------------------------------------------------------------------------
class TestNestedBlocks:
    """Nested array and object blocks."""

    def test_simple_array_of_objects(self):
        text = """\
Items
[
	{
		ID 1
		Amount 4
	}
	{
		ID 2
		Amount 3
	}
]"""
        result = parse_dat(text)
        assert isinstance(result["Items"], list)
        assert len(result["Items"]) == 2
        assert result["Items"][0]["ID"] == 1
        assert result["Items"][0]["Amount"] == 4
        assert result["Items"][1]["ID"] == 2
        assert result["Items"][1]["Amount"] == 3

    def test_array_of_strings(self):
        text = """\
DefaultPaintColors
[
	"#475e83"
	"#a69884"
	"#437c44"
]"""
        result = parse_dat(text)
        assert isinstance(result["DefaultPaintColors"], list)
        assert len(result["DefaultPaintColors"]) == 3
        assert result["DefaultPaintColors"][0] == "#475e83"
        assert result["DefaultPaintColors"][1] == "#a69884"
        assert result["DefaultPaintColors"][2] == "#437c44"

    def test_array_of_numbers(self):
        text = """\
ForwardGearRatios
[
	20
	12.56
]"""
        result = parse_dat(text)
        assert isinstance(result["ForwardGearRatios"], list)
        assert len(result["ForwardGearRatios"]) == 2
        assert result["ForwardGearRatios"][0] == 20
        assert result["ForwardGearRatios"][1] == 12.56

    def test_nested_object(self):
        text = """\
EngineSound
{
	IdlePitch 1.0
	IdleVolume 0.75
	MaxPitch 2
	MaxVolume 1.0
}"""
        result = parse_dat(text)
        assert isinstance(result["EngineSound"], dict)
        assert result["EngineSound"]["IdlePitch"] == 1.0
        assert result["EngineSound"]["IdleVolume"] == 0.75
        assert result["EngineSound"]["MaxPitch"] == 2
        assert result["EngineSound"]["MaxVolume"] == 1.0

    def test_deeply_nested(self):
        """array -> object -> array -> object"""
        text = """\
Blueprints
[
	{
		Name Repair
		InputItems
		[
			{
				ID 10
				Amount 4
			}
		]
	}
]"""
        result = parse_dat(text)
        blueprints = result["Blueprints"]
        assert isinstance(blueprints, list)
        assert len(blueprints) == 1
        bp = blueprints[0]
        assert bp["Name"] == "Repair"
        assert isinstance(bp["InputItems"], list)
        assert len(bp["InputItems"]) == 1
        assert bp["InputItems"][0]["ID"] == 10
        assert bp["InputItems"][0]["Amount"] == 4

    def test_mixed_array(self):
        """Array with objects, quoted strings, and bare values."""
        text = """\
Things
[
	{
		Name Alpha
	}
	"some string"
	42
]"""
        result = parse_dat(text)
        things = result["Things"]
        assert isinstance(things, list)
        assert len(things) == 3
        assert isinstance(things[0], dict)
        assert things[0]["Name"] == "Alpha"
        assert things[1] == "some string"
        assert things[2] == 42

    def test_inline_comments_in_blocks(self):
        text = """\
Items
[
	{
		ID "abc123" // Metal Scrap
		Amount 4
	}
]"""
        result = parse_dat(text)
        items = result["Items"]
        assert len(items) == 1
        assert items[0]["ID"] == "abc123"
        assert items[0]["Amount"] == 4

    def test_array_of_strings_with_comments(self):
        text = """\
RequiresNearbyCraftingTags
[
	"7b82c125a5a54984b8bb26576b59e977" // Workbench
]"""
        result = parse_dat(text)
        tags = result["RequiresNearbyCraftingTags"]
        assert isinstance(tags, list)
        assert len(tags) == 1
        assert tags[0] == "7b82c125a5a54984b8bb26576b59e977"

    def test_key_value_with_inline_bracket(self):
        """Key followed by [ on same line (e.g. 'Key [')."""
        text = """\
Items [
	{
		ID 1
	}
]"""
        result = parse_dat(text)
        assert isinstance(result["Items"], list)
        assert len(result["Items"]) == 1
        assert result["Items"][0]["ID"] == 1

    def test_key_value_with_inline_brace(self):
        """Key followed by { on same line (e.g. 'Key {')."""
        text = """\
Sound {
	Volume 0.5
	Pitch 1.0
}"""
        result = parse_dat(text)
        assert isinstance(result["Sound"], dict)
        assert result["Sound"]["Volume"] == 0.5
        assert result["Sound"]["Pitch"] == 1.0


# ---------------------------------------------------------------------------
# TestRealFixtures
# ---------------------------------------------------------------------------
class TestRealFixtures:
    """End-to-end parsing of real fixture files."""

    def test_canned_beans(self):
        path = FIXTURES / "food_beans" / "Canned_Beans.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Food"
        assert result["ID"] == 13
        assert result["Health"] == 10
        assert result["Food"] == 55
        assert result["GUID"] == "78fefdd23def4ab6ac8301adfcc3b2d4"
        assert result["ConsumeAudioClip"] == "Sounds/EatCrunchy.mp3"

    def test_maplestrike(self):
        path = FIXTURES / "gun_maplestrike" / "Maplestrike.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Gun"
        assert result["Player_Damage"] == 40
        assert result["Firerate"] == 5
        assert result["Semi"] is True
        assert result["Auto"] is True
        assert result["Safety"] is True
        # Blueprints array
        assert isinstance(result["Blueprints"], list)
        assert len(result["Blueprints"]) == 2
        # First blueprint has nested InputItems array
        bp0 = result["Blueprints"][0]
        assert bp0["Name"] == "Repair"
        assert isinstance(bp0["InputItems"], list)
        assert len(bp0["InputItems"]) == 2
        # Second blueprint
        bp1 = result["Blueprints"][1]
        assert bp1["Name"] == "Salvage"

    def test_bandage(self):
        path = FIXTURES / "medical_bandage" / "Bandage.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Medical"
        assert result["Health"] == 15
        assert result["Bleeding_Modifier"] == "Heal"
        assert result["Aid"] is True
        # 1 blueprint
        assert isinstance(result["Blueprints"], list)
        assert len(result["Blueprints"]) == 1

    def test_humvee(self):
        path = FIXTURES / "vehicle_humvee" / "Humvee.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Vehicle"
        assert result["Speed_Max"] == 14
        assert result["Fuel"] == 2000
        # 4 WheelConfigurations
        assert isinstance(result["WheelConfigurations"], list)
        assert len(result["WheelConfigurations"]) == 4
        # Verify first wheel config
        wc0 = result["WheelConfigurations"][0]
        assert wc0["WheelColliderPath"] == "Tires/Tire_0"
        assert wc0["IsColliderSteered"] is True
        assert wc0["IsColliderPowered"] is True
        # EngineSound dict
        assert isinstance(result["EngineSound"], dict)
        assert result["EngineSound"]["IdlePitch"] == 1.0
        assert result["EngineSound"]["MaxPitch"] == 2
        # DefaultPaintColors list
        assert isinstance(result["DefaultPaintColors"], list)
        assert len(result["DefaultPaintColors"]) == 4
        assert result["DefaultPaintColors"][0] == "#475e83"
        # ForwardGearRatios list
        assert isinstance(result["ForwardGearRatios"], list)
        assert len(result["ForwardGearRatios"]) == 2
        assert result["ForwardGearRatios"][0] == 20
        assert result["ForwardGearRatios"][1] == 12.56
        # PaintableSections
        assert isinstance(result["PaintableSections"], list)
        assert len(result["PaintableSections"]) == 2

    def test_bear(self):
        path = FIXTURES / "animal_bear" / "Bear.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Animal"
        assert result["Health"] == 100
        assert result["Speed_Run"] == 12
        assert result["Damage"] == 20
        assert result["ID"] == 5

    def test_katana(self):
        path = FIXTURES / "melee_katana" / "Katana.dat"
        result = parse_dat_file(path)
        assert result["Type"] == "Melee"
        assert result["Player_Damage"] == 50
        assert result["Strength"] == 1.5
        assert result["Range"] == 2.25
        # Blueprints
        assert isinstance(result["Blueprints"], list)
        assert len(result["Blueprints"]) == 2
        # First blueprint has nested RequiresNearbyCraftingTags array
        bp0 = result["Blueprints"][0]
        assert isinstance(bp0["RequiresNearbyCraftingTags"], list)
        assert len(bp0["RequiresNearbyCraftingTags"]) == 1


# ---------------------------------------------------------------------------
# TestAssetFileParsing
# ---------------------------------------------------------------------------
class TestAssetFileParsing:
    """Tests for .asset file format (quoted keys)."""

    def test_parse_asset_format(self):
        """Keys in .asset files are quoted — parser should strip them."""
        text = '''
"Metadata"
{
    "GUID" "dcddca4d05564563aa2aac8144615c46"
    "Type" "SDG.Unturned.CraftingBlacklistAsset"
}
"Asset"
{
    "Allow_Core_Blueprints" "False"
    "Input_Items"
    [
        {
        "NoteToSelf" "car battery"
        "GUID" "098b13be34a7411db7736b7f866ada69"
        }
    ]
}
'''
        result = parse_dat(text)
        # Keys should NOT have quotes
        assert "Metadata" in result
        assert "Asset" in result
        assert result["Metadata"]["GUID"] == "dcddca4d05564563aa2aac8144615c46"
        assert result["Asset"]["Allow_Core_Blueprints"] is False
        assert len(result["Asset"]["Input_Items"]) == 1
        assert result["Asset"]["Input_Items"][0]["GUID"] == "098b13be34a7411db7736b7f866ada69"

    def test_parse_level_asset_format(self):
        """LevelAsset with Crafting_Blacklists array."""
        text = '''
"Metadata"
{
    "GUID" "77e3a2e0fd6b4c768928dc2861888a6e"
    "Type" "SDG.Unturned.LevelAsset"
}
"Asset"
{
    "Crafting_Blacklists"
    [
        {"GUID" "dcddca4d05564563aa2aac8144615c46"}
    ]
}
'''
        result = parse_dat(text)
        assert result["Metadata"]["GUID"] == "77e3a2e0fd6b4c768928dc2861888a6e"
        blacklists = result["Asset"]["Crafting_Blacklists"]
        assert len(blacklists) == 1
        assert blacklists[0]["GUID"] == "dcddca4d05564563aa2aac8144615c46"

    def test_existing_dat_format_unaffected(self):
        """Unquoted .dat keys still parse correctly after the change."""
        text = '''GUID f019fcaa2e8e4c92b17259025c80ff77
Type Spawn
ID 228
Tables 2
Table_0_Spawn_ID 229
Table_0_Weight 31
'''
        result = parse_dat(text)
        assert result["GUID"] == "f019fcaa2e8e4c92b17259025c80ff77"
        assert result["Type"] == "Spawn"
        assert result["ID"] == 228
