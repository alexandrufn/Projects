"""Loto 6/49 number generator - one button, six numbers from the Romanian draw history."""
import tkinter as tk
from tkinter import messagebox

import predictor

BG, FG, GOLD = "#14102a", "#f2efff", "#ffd650"
BALL_COLORS = ("#e8453c", "#f08a24", "#f2c335", "#3fae5a", "#2f86d6", "#8e5bd6")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Loto 6/49")
        self.configure(bg=BG)
        self.resizable(False, False)
        try:
            self.draws = predictor.load_draws()
        except OSError:
            messagebox.showerror("Loto 6/49", "Lipseste data/loto649.csv.\nRuleaza: python scrape.py")
            raise SystemExit(1)
        tk.Label(self, text="LOTO 6/49", font=("Segoe UI", 26, "bold"), bg=BG, fg=GOLD).pack(pady=(22, 2))
        tk.Label(self, text="%d extrageri analizate (%s - %s)" % (len(self.draws), "1998", "azi"),
                 font=("Segoe UI", 10), bg=BG, fg="#a9a3c9").pack()
        self.canvas = tk.Canvas(self, width=440, height=90, bg=BG, highlightthickness=0)
        self.canvas.pack(pady=18, padx=20)
        tk.Button(self, text="Genereaza numerele loto", font=("Segoe UI", 14, "bold"), bg=GOLD, fg="#201a3a",
                  activebackground="#ffe58a", relief="flat", padx=24, pady=10, cursor="hand2",
                  command=self.generate).pack(pady=(0, 10))
        tk.Label(self, text="Loteria este aleatorie: nicio metoda nu garanteaza castigul. Joaca responsabil.",
                 font=("Segoe UI", 8), bg=BG, fg="#7f79a3").pack(pady=(4, 16))
        self.draw_balls([])

    def draw_balls(self, nums):
        self.canvas.delete("all")
        for i in range(6):
            x = 40 + i * 72
            n = nums[i] if nums else None
            self.canvas.create_oval(x - 30, 15, x + 30, 75, fill=BALL_COLORS[i] if n else "#2a2448",
                                    outline="#ffffff" if n else "#3c3563", width=2)
            self.canvas.create_text(x, 45, text=str(n) if n else "?", fill="white" if n else "#6d6794",
                                    font=("Segoe UI", 20, "bold"))

    def generate(self):
        self.draw_balls(predictor.generate(self.draws))


if __name__ == "__main__":
    App().mainloop()
