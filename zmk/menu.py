"""
Terminal menus
"""

from typing import Any, Generic, Iterable, Optional, TypeVar

import rich
from rich.console import Console
from rich.theme import Theme

from . import terminal


class StopMenu(KeyboardInterrupt):
    """
    Exception thrown when the user cancels the menu without making a selection
    """


T = TypeVar("T")


class TerminalMenu(Generic[T]):
    """
    Manages an interactive menu in a terminal window.
    """

    CONTROLS = "[↑↓: select] [Enter: confirm] [Esc: cancel]"
    EXTRA_LINES = 2  # One line of context before the menu + controls line at end
    DEFAULT_THEME = Theme(
        {
            "title": "bright_magenta",
            "focus": "bright_cyan",
            "unfocus": "default",
            "ellipsis": "dim",
            "controls": "dim",
        }
    )

    title: Any
    items: list[T]
    default_index: int
    _focus_index: int
    _scroll_index: int
    _num_title_lines: int

    # TODO: add an option for a text filter field
    def __init__(
        self,
        title: Any,
        items: Iterable[T],
        default_index=0,
        console: Optional[Console] = None,
        theme: Optional[Theme] = None,
    ):
        """
        An interactive terminal menu.

        :param title: Text to display at the top of the menu.
        :param items: List of items to display. Items should either be strings or
            implement __rich__() to return the data to display.
        :param default_index: Index of the item to focus initially.
        :param console: Console in which to display the menu.
        :param theme: Theme to apply. See TerminalMenu.DEFAULT_THEME for style names.
        """
        self.title = title
        self.items = list(items)
        self.console = console or rich.get_console()
        self.theme = theme or self.DEFAULT_THEME
        self.default_index = default_index
        self._focus_index = 0
        self._scroll_index = 0
        self._num_title_lines = len(self.console.render_lines(self.title))

    def show(self):
        """
        Displays the menu.

        :return: The selected item.
        :raises StopMenu: The user canceled the menu without making a selection.
        """

        try:
            with terminal.hide_cursor(), self.console.use_theme(self.theme):
                self._focus_index = self.default_index

                while True:
                    self._update_scroll_index()
                    self._print_menu()

                    if self._handle_input():
                        return self.items[self._focus_index]

                    self._reset_cursor_to_top()
        finally:
            # Add one blank line at the end to separate further output from the menu.
            self._erase_controls()

    @property
    def _menu_height(self):
        return self.console.height - self.EXTRA_LINES - self._num_title_lines

    def _print_menu(self):
        self.console.print(
            self.title,
            style="title",
            justify="left",
            overflow="ellipsis",
            highlight=False,
        )

        display_count = self._get_display_count()

        for row in range(display_count):
            index = self._scroll_index + row
            focused = index == self._focus_index

            at_start = self._scroll_index == 0
            at_end = self._scroll_index + display_count >= len(self.items)
            show_more = (not at_start and row == 0) or (
                not at_end and row == display_count - 1
            )

            self._print_item(self.items[index], focused=focused, show_more=show_more)

        self.console.print(self.CONTROLS, style="controls", end="", overflow="crop")

    def _print_item(self, item: T, focused: bool, show_more: bool):
        style = "ellipsis" if show_more else "focus" if focused else "unfocus"

        indent = "> " if focused else "  "
        item = "..." if show_more else item

        self.console.print(
            indent,
            item,
            sep="",
            style=style,
            justify="left",
            overflow="ellipsis",
            highlight=False,
        )

    def _handle_input(self):
        key = terminal.read_key()

        if key == terminal.RETURN:
            return True

        if key == terminal.ESCAPE:
            raise StopMenu()

        if key == terminal.UP:
            self._focus_index -= 1
        elif key == terminal.DOWN:
            self._focus_index += 1
        elif key == terminal.PAGE_UP:
            self._focus_index -= self._menu_height
        elif key == terminal.PAGE_DOWN:
            self._focus_index += self._menu_height
        elif key == terminal.HOME:
            self._focus_index = 0
        elif key == terminal.END:
            self._focus_index = len(self.items) - 1

        self._focus_index = min(max(0, self._focus_index), len(self.items) - 1)
        return False

    def _get_display_count(self):
        return min(len(self.items), self._menu_height)

    def _update_scroll_index(self):
        self._scroll_index = self._get_scroll_index()

    def _get_scroll_index(self):
        items_count = len(self.items)
        display_count = self._get_display_count()

        if items_count < display_count:
            return 0

        first_displayed = self._scroll_index
        last_displayed = first_displayed + display_count - 1

        if self._focus_index <= first_displayed:
            return max(0, self._focus_index - 1)

        if self._focus_index >= last_displayed:
            return min(items_count - 1, self._focus_index + 1) - (display_count - 1)

        return self._scroll_index

    def _reset_cursor_to_top(self):
        display_count = self._get_display_count()

        row, _ = terminal.get_cursor_pos()
        row = max(0, row - display_count - self._num_title_lines)

        terminal.set_cursor_pos(row=row)

    def _erase_controls(self):
        terminal.set_cursor_column(0)
        self.console.print(justify="left")


def show_menu(
    title: str,
    items: Iterable[T],
    default_index=0,
    console: Optional[Console] = None,
    theme: Optional[Theme] = None,
):
    """
    Displays an interactive menu.

    :param title: Text to display at the top of the menu.
    :param items: List of items to display. Items should either be strings or
        implement __rich__() to return the data to display.
    :param default_index: Index of the item to focus initially.
    :param console: Console in which to display the menu.
    :param theme: Theme to apply. See TerminalMenu.DEFAULT_THEME for style names.
    :return: The selected item.
    :raises StopMenu: The user canceled the menu without making a selection.
    """
    menu = TerminalMenu(
        title=title,
        items=items,
        default_index=default_index,
        console=console,
        theme=theme,
    )
    return menu.show()
