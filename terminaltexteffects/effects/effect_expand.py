import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return ExpandEffect, ExpandEffectArgs


@argclass(
    name="expand",
    formatter_class=argtypes.CustomFormatter,
    help="Expands the text from a single point.",
    description="expand | Expands the text from a single point.",
    epilog=f"""{argtypes.EASING_EPILOG}
    
Example: terminaltexteffects expand --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 5 --movement-speed 0.35 --easing IN_OUT_QUART""",
)
@dataclass
class ExpandEffectArgs(ArgsDataClass):
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argtypes.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argtypes.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argtypes.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argtypes.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argtypes.PositiveInt.type_parser,
        default=5,
        metavar=argtypes.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argtypes.PositiveFloat.type_parser,
        default=0.35,
        metavar=argtypes.PositiveFloat.METAVAR,
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    expand_easing: typing.Callable = ArgField(
        cmd_name="--expand-easing",
        default=easing.in_out_quart,
        type_parser=argtypes.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return ExpandEffect


class ExpandEffect:
    """Effect that draws the characters expanding from a single point."""

    def __init__(self, terminal: Terminal, args: ExpandEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        for character in self.terminal.get_characters():
            character.motion.set_coordinate(self.terminal.output_area.center)
            input_coord_path = character.motion.new_path(
                speed=self.args.movement_speed,
                ease=self.args.expand_easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
            self.terminal.set_character_visibility(character, True)
            character.motion.activate_path(input_coord_path)
            self.active_chars.append(character)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            gradient_scn = character.animation.new_scene()
            gradient = graphics.Gradient(
                final_gradient.spectrum[0], self.character_final_color_map[character], steps=10
            )
            gradient_scn.apply_gradient_to_symbols(gradient, character.input_symbol, self.args.final_gradient_frames)
            character.animation.activate_scene(gradient_scn)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.active_chars:
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        for character in self.active_chars:
            character.tick()
