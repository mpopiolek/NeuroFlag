from __future__ import annotations

import customtkinter as ctk

from app.ui import theme as t

_STEP_LABELS = ("Dane", "Plik", "Analiza", "Wynik")
_CIRCLE_SIZE = 28
_CHECKMARK = "✓"


class WorkflowStepper(ctk.CTkFrame):
    """Poziomy wskaźnik postępu wizarda (4 kroki, bez kliknięć)."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs: object) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._active_step = 1
        self._completed_through = 0
        self._step_frames: list[ctk.CTkFrame] = []
        self._circles: list[ctk.CTkFrame] = []
        self._circle_labels: list[ctk.CTkLabel] = []
        self._title_labels: list[ctk.CTkLabel] = []
        self._connectors: list[ctk.CTkFrame] = []

        for index in range(len(_STEP_LABELS)):
            if index > 0:
                connector = ctk.CTkFrame(self, fg_color=t.COLOR_BORDER, height=2, width=32)
                connector.grid(row=0, column=index * 2 - 1, pady=(0, 18))
                self._connectors.append(connector)

            step_col = index * 2
            step_frame = ctk.CTkFrame(self, fg_color="transparent")
            step_frame.grid(row=0, column=step_col, padx=4)
            self._step_frames.append(step_frame)

            circle = ctk.CTkFrame(
                step_frame,
                width=_CIRCLE_SIZE,
                height=_CIRCLE_SIZE,
                corner_radius=_CIRCLE_SIZE // 2,
                fg_color=t.COLOR_TEXT_MUTED,
            )
            circle.pack()
            circle.pack_propagate(False)
            self._circles.append(circle)

            circle_label = ctk.CTkLabel(
                circle,
                text=str(index + 1),
                font=t.font_caption(),
                text_color=t.COLOR_ON_ACCENT,
            )
            circle_label.place(relx=0.5, rely=0.5, anchor="center")
            self._circle_labels.append(circle_label)

            title = ctk.CTkLabel(
                step_frame,
                text=_STEP_LABELS[index],
                font=t.font_caption(),
                text_color=t.COLOR_TEXT_MUTED,
            )
            title.pack(pady=(4, 0))
            self._title_labels.append(title)

        self._refresh()

    def set_active_step(self, step: int) -> None:
        if step < 1 or step > len(_STEP_LABELS):
            msg = f"step must be 1–{len(_STEP_LABELS)}, got {step}"
            raise ValueError(msg)
        self._active_step = step
        self._refresh()

    def set_completed_through(self, step: int) -> None:
        if step < 0 or step > len(_STEP_LABELS):
            msg = f"completed_through must be 0–{len(_STEP_LABELS)}, got {step}"
            raise ValueError(msg)
        self._completed_through = step
        self._refresh()

    def _refresh(self) -> None:
        for index in range(len(_STEP_LABELS)):
            step_num = index + 1
            circle = self._circles[index]
            circle_label = self._circle_labels[index]
            title = self._title_labels[index]

            if step_num == self._active_step:
                circle.configure(fg_color=t.COLOR_NAVY)
                circle_label.configure(
                    text=str(step_num),
                    text_color=t.COLOR_ON_ACCENT,
                    font=t.font_caption(),
                )
                title.configure(
                    text=_STEP_LABELS[index],
                    font=t.font_subheading(),
                    text_color=t.COLOR_NAVY,
                )
            elif step_num < self._active_step or (
                step_num <= self._completed_through and step_num != self._active_step
            ):
                circle.configure(fg_color=t.COLOR_NAVY)
                circle_label.configure(
                    text=_CHECKMARK,
                    text_color=t.COLOR_ON_ACCENT,
                    font=t.font_body(),
                )
                title.configure(
                    text=_STEP_LABELS[index],
                    font=t.font_caption(),
                    text_color=t.COLOR_TEXT_SECONDARY,
                )
            else:
                circle.configure(fg_color=t.COLOR_BORDER)
                circle_label.configure(
                    text=str(step_num),
                    text_color=t.COLOR_TEXT_MUTED,
                    font=t.font_caption(),
                )
                title.configure(
                    text=_STEP_LABELS[index],
                    font=t.font_caption(),
                    text_color=t.COLOR_TEXT_MUTED,
                )

        for connector in self._connectors:
            connector.configure(fg_color=t.COLOR_BORDER)
