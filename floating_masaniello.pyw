import sys
import os
import math
import tkinter as tk
from tkinter import ttk, messagebox
import winsound

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ExactExcelMasanielloEngine:
    def __init__(self, initial_capital, total_trades, expected_wins, quota_or_payout, custom_profit_pct=None, use_exact_round=False):
        self.B_init = float(initial_capital)
        self.N = min(100, max(1, int(total_trades)))
        self.K = min(self.N, max(1, int(expected_wins)))
        self.use_exact_round = use_exact_round
        
        val = float(quota_or_payout)
        if val > 10.0:
            self.payout_pct = val
            self.Q = 1.0 + (val / 100.0)
        else:
            self.Q = val
            self.payout_pct = (val - 1.0) * 100.0
            
        self.history = []
        self.build_matrix()
        
        if custom_profit_pct is not None and float(custom_profit_pct) > 0:
            self.custom_profit_pct = float(custom_profit_pct)
            self.scale_factor = self.custom_profit_pct / self.yield_pct if self.yield_pct > 0 else 1.0
            self.target_capital = self.B_init * (1.0 + self.custom_profit_pct / 100.0)
            self.win_profit = self.target_capital - self.B_init
            self.effective_yield_pct = self.custom_profit_pct
        else:
            self.custom_profit_pct = None
            self.scale_factor = 1.0
            self.effective_yield_pct = self.yield_pct

    def build_matrix(self):
        N, K, Q = self.N, self.K, self.Q
        self.V = [[0.0] * (K + 2) for _ in range(N + 2)]
        
        for w in range(K + 1):
            if w >= K:
                for m in range(N + 1):
                    self.V[m][w] = 1.0
            else:
                self.V[N][w] = 0.0

        for m in range(N - 1, -1, -1):
            for w in range(K - 1, -1, -1):
                rem_trades = N - m
                rem_wins = K - w
                if rem_wins == rem_trades:
                    self.V[m][w] = Q ** rem_trades
                elif rem_wins > rem_trades:
                    self.V[m][w] = 0.0
                else:
                    v_loss = self.V[m + 1][w]
                    v_win = self.V[m + 1][w + 1]
                    denom = v_loss + (Q - 1.0) * v_win
                    if denom != 0:
                        self.V[m][w] = (Q * v_loss * v_win) / denom
                    else:
                        self.V[m][w] = 0.0

        self.target_capital = self.B_init * self.V[0][0]
        self.win_profit = self.target_capital - self.B_init
        self.yield_pct = (self.V[0][0] - 1.0) * 100.0

    def get_state(self):
        curr_balance = self.B_init
        wins = 0
        losses = 0
        for item in self.history:
            trade_stake = float(item['raw_stake'] if not self.use_exact_round else item['stake'])
            if item['result'] == 'W':
                curr_balance += trade_stake * (self.Q - 1.0)
                wins += 1
            elif item['result'] == 'L':
                curr_balance -= trade_stake
                losses += 1
        return curr_balance, wins, losses

    def get_stake_at_state(self, curr_balance, wins, losses):
        m = wins + losses
        w = wins
        if wins >= self.K:
            return 0, 0.0, True, "TARGET_WON"
        if losses > (self.N - self.K) or m >= self.N:
            return 0, 0.0, True, "SESSION_FAILED"
            
        v_win_next = self.V[m + 1][w + 1]
        v_loss_next = self.V[m + 1][w]
        denom = v_loss_next + (self.Q - 1.0) * v_win_next
        if denom == 0:
            return 0, 0.0, True, "CALC_ERROR"
            
        ratio = 1.0 - (self.Q * v_win_next / denom)
        raw_stake = ratio * curr_balance * self.scale_factor
        rounded_stake = int(round(raw_stake))
        if raw_stake > 0 and rounded_stake < 1:
            rounded_stake = 1
        return rounded_stake, raw_stake, False, "OK"

    def get_next_stake(self):
        curr_balance, wins, losses = self.get_state()
        return self.get_stake_at_state(curr_balance, wins, losses)

    def get_win_loss_predictions(self):
        curr_balance, wins, losses = self.get_state()
        rounded_stake, raw_stake, is_done, msg = self.get_next_stake()
        
        if is_done or raw_stake <= 0:
            return None, None
            
        stake_used = float(rounded_stake if self.use_exact_round else raw_stake)
        bal_if_win = curr_balance + stake_used * (self.Q - 1.0)
        s_win_round, s_win_raw, win_done, _ = self.get_stake_at_state(bal_if_win, wins + 1, losses)
        
        bal_if_loss = curr_balance - stake_used
        s_loss_round, s_loss_raw, loss_done, _ = self.get_stake_at_state(bal_if_loss, wins, losses + 1)
        
        pred_win = {'balance': bal_if_win, 'next_stake_round': s_win_round, 'next_stake_raw': s_win_raw, 'is_done': win_done}
        pred_loss = {'balance': bal_if_loss, 'next_stake_round': s_loss_round, 'next_stake_raw': s_loss_raw, 'is_done': loss_done}
        
        return pred_win, pred_loss

    def record_trade(self, result):
        curr_balance, wins, losses = self.get_state()
        rounded_stake, raw_stake, is_done, msg = self.get_next_stake()
        if is_done or raw_stake <= 0:
            return False
            
        trade_stake = float(rounded_stake if self.use_exact_round else raw_stake)
        pnl = trade_stake * (self.Q - 1.0) if result == 'W' else -trade_stake
        end_balance = curr_balance + pnl
        
        self.history.append({
            'step': len(self.history) + 1,
            'result': result,
            'stake': rounded_stake,
            'raw_stake': raw_stake,
            'pnl': pnl,
            'balance': end_balance,
            'wins_after': wins + (1 if result == 'W' else 0),
            'losses_after': losses + (1 if result == 'L' else 0)
        })
        return True

    def undo_last(self):
        if self.history:
            self.history.pop()
            return True
        return False


class AegisQuantApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aegis Quant Pro - Portfolio Safeguard")
        self.geometry("340x550")
        self.minsize(310, 390)
        self.attributes("-topmost", True)
        self.is_topmost = True
        self.is_compact = False
        self.sound_enabled = True
        self.auto_copy_enabled = True
        
        ico_path = resource_path("app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
                
        self.engine = None
        self.currency_symbol = "$"
        
        self.setup_styles()
        self.build_ui()
        
    def play_sound(self, sound_type):
        if not self.sound_enabled:
            return
        try:
            if sound_type == "win":
                winsound.Beep(1000, 100)
                winsound.Beep(1400, 150)
            elif sound_type == "loss":
                winsound.Beep(450, 200)
            elif sound_type == "target_win":
                winsound.Beep(800, 100)
                winsound.Beep(1000, 100)
                winsound.Beep(1200, 100)
                winsound.Beep(1500, 250)
            elif sound_type == "target_loss":
                winsound.Beep(400, 150)
                winsound.Beep(300, 250)
        except Exception:
            pass

    def setup_styles(self):
        self.configure(bg="#0b0f19")
        style = ttk.Style(self)
        style.theme_use("clam")
        
        self.c_bg = "#0b0f19"
        self.c_card = "#151d2a"
        self.c_accent = "#eab308" # Luxury Gold accent
        self.c_win = "#10b981"    # Emerald green
        self.c_loss = "#f43f5e"   # Coral red
        self.c_text = "#f8fafc"
        self.c_subtext = "#94a3b8"
        
        style.configure(".", background=self.c_bg, foreground=self.c_text)
        style.configure("TLabel", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 9))

    def build_ui(self):
        # Top Luxury Control Bar
        top_bar = tk.Frame(self, bg="#070a12", height=28)
        top_bar.pack(fill="x", side="top")
        
        title_lbl = tk.Label(top_bar, text="🛡️ Aegis Quant Pro", bg="#070a12", fg="#eab308", font=("Segoe UI", 9, "bold"))
        title_lbl.pack(side="left", padx=6, pady=2)
        
        self.topmost_btn = tk.Button(top_bar, text="📌 Top: ON", bg="#151d2a", fg="#f8fafc", font=("Segoe UI", 7, "bold"),
                                     command=self.toggle_topmost, relief="flat", padx=3, pady=1)
        self.topmost_btn.pack(side="right", padx=2, pady=2)
        
        self.compact_btn = tk.Button(top_bar, text="🗖 Mini", bg="#151d2a", fg="#f8fafc", font=("Segoe UI", 7, "bold"),
                                      command=self.toggle_compact, relief="flat", padx=3, pady=1)
        self.compact_btn.pack(side="right", padx=1, pady=2)
        
        # Main Container
        self.main_container = tk.Frame(self, bg=self.c_bg)
        self.main_container.pack(fill="both", expand=True, padx=6, pady=4)
        
        # Setup Card
        self.setup_frame = tk.Frame(self.main_container, bg=self.c_card, padx=6, pady=6)
        self.setup_frame.pack(fill="x", pady=(0, 4))
        
        # Row 1: Capital, Currency
        tk.Label(self.setup_frame, text="Capital:", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.ent_capital = tk.Entry(self.setup_frame, width=5, bg="#0b0f19", fg="#ffffff", insertbackground="#ffffff", relief="flat", font=("Segoe UI", 8))
        self.ent_capital.insert(0, "58")
        self.ent_capital.grid(row=0, column=1, sticky="w", padx=(2, 6))
        self.ent_capital.bind("<KeyRelease>", lambda e: self.start_session())
        
        tk.Label(self.setup_frame, text="Curr:", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=0, column=2, sticky="w")
        self.combo_currency = ttk.Combobox(self.setup_frame, values=["$", "৳", "€", "₹"], width=3, state="readonly", font=("Segoe UI", 8))
        self.combo_currency.current(0)
        self.combo_currency.bind("<<ComboboxSelected>>", self.on_currency_change)
        self.combo_currency.grid(row=0, column=3, sticky="w")
        
        # Row 2: Trades (N), Wins (K) - COMPLETE FREEDOM!
        tk.Label(self.setup_frame, text="Trades (N):", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.ent_trades = tk.Entry(self.setup_frame, width=5, bg="#0b0f19", fg="#ffffff", insertbackground="#ffffff", relief="flat", font=("Segoe UI", 8))
        self.ent_trades.insert(0, "15")
        self.ent_trades.grid(row=1, column=1, sticky="w", padx=(2, 6), pady=2)
        self.ent_trades.bind("<KeyRelease>", lambda e: self.start_session())
        
        tk.Label(self.setup_frame, text="Wins (K):", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=1, column=2, sticky="w", pady=2)
        self.ent_wins = tk.Entry(self.setup_frame, width=3, bg="#0b0f19", fg="#ffffff", insertbackground="#ffffff", relief="flat", font=("Segoe UI", 8, "bold"))
        self.ent_wins.insert(0, "5") # User sets any Win Target!
        self.ent_wins.grid(row=1, column=3, sticky="w", pady=2)
        self.ent_wins.bind("<KeyRelease>", lambda e: self.start_session())
        
        # Row 3: Target Prof % & Payout % - COMPLETE FREEDOM!
        tk.Label(self.setup_frame, text="Target Prof %:", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=2, column=0, sticky="w")
        self.ent_profit_pct = tk.Entry(self.setup_frame, width=5, bg="#0b0f19", fg="#38bdf8", font=("Segoe UI", 8, "bold"), insertbackground="#ffffff", relief="flat")
        self.ent_profit_pct.insert(0, "20") # User sets any Target Profit %!
        self.ent_profit_pct.grid(row=2, column=1, sticky="w", padx=(2, 6))
        self.ent_profit_pct.bind("<KeyRelease>", lambda e: self.start_session())
        
        tk.Label(self.setup_frame, text="Payout %:", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8)).grid(row=2, column=2, sticky="w")
        self.ent_payout = tk.Entry(self.setup_frame, width=3, bg="#0b0f19", fg="#22c55e", font=("Segoe UI", 8, "bold"), insertbackground="#ffffff", relief="flat")
        self.ent_payout.insert(0, "75")
        self.ent_payout.grid(row=2, column=3, sticky="w")
        self.ent_payout.bind("<KeyRelease>", lambda e: self.start_session())
        
        # Options row
        opts_sub = tk.Frame(self.setup_frame, bg=self.c_card)
        opts_sub.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(3, 1))
        
        self.chk_sound_var = tk.BooleanVar(value=True)
        chk_sound = tk.Checkbutton(opts_sub, text="🔊 Sound", variable=self.chk_sound_var, bg=self.c_card, fg=self.c_text, font=("Segoe UI", 7),
                                   selectcolor="#0b0f19", activebackground=self.c_card, activeforeground=self.c_text,
                                   command=self.toggle_sound)
        chk_sound.pack(side="left")
        
        self.chk_copy_var = tk.BooleanVar(value=True)
        chk_copy = tk.Checkbutton(opts_sub, text="📋 Auto-Copy", variable=self.chk_copy_var, bg=self.c_card, fg=self.c_text, font=("Segoe UI", 7),
                                  selectcolor="#0b0f19", activebackground=self.c_card, activeforeground=self.c_text,
                                  command=self.toggle_autocopy)
        chk_copy.pack(side="left", padx=2)
        
        self.chk_round_var = tk.BooleanVar(value=False)
        chk_round = tk.Checkbutton(opts_sub, text="🔢 Round", variable=self.chk_round_var, bg=self.c_card, fg=self.c_text, font=("Segoe UI", 7),
                                   selectcolor="#0b0f19", activebackground=self.c_card, activeforeground=self.c_text,
                                   command=self.toggle_rounding)
        chk_round.pack(side="left", padx=2)
        
        btn_start = tk.Button(opts_sub, text="🚀 START", bg="#0284c7", fg="#ffffff", font=("Segoe UI", 8, "bold"),
                              relief="flat", pady=0, padx=4, command=self.start_session)
        btn_start.pack(side="right")
        
        # Compact Stake Card
        self.stake_frame = tk.Frame(self.main_container, bg=self.c_card, padx=6, pady=6)
        self.stake_frame.pack(fill="x", pady=(0, 4))
        
        self.lbl_step_info = tk.Label(self.stake_frame, text="Trade #1 of 15", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 8, "bold"))
        self.lbl_step_info.pack()
        
        stake_row = tk.Frame(self.stake_frame, bg=self.c_card)
        stake_row.pack(pady=1)
        
        self.lbl_stake_val = tk.Label(stake_row, text="$8.74", bg=self.c_card, fg=self.c_win, font=("Segoe UI", 22, "bold"))
        self.lbl_stake_val.pack(side="left")
        
        self.btn_copy_stake = tk.Button(stake_row, text="📋 Copy", bg="#334155", fg="#38bdf8", font=("Segoe UI", 7, "bold"),
                                        relief="flat", padx=3, pady=0, command=self.copy_stake_to_clipboard)
        self.btn_copy_stake.pack(side="left", padx=(4, 0))
        
        self.lbl_stake_desc = tk.Label(self.stake_frame, text="👉 SUGGESTED STAKE (AEGIS QUANT ENGINE)", bg=self.c_card, fg=self.c_accent, font=("Segoe UI", 7, "bold"))
        self.lbl_stake_desc.pack(pady=(1, 4))
        
        # Next Predictions Frame
        pred_frame = tk.Frame(self.stake_frame, bg=self.c_card)
        pred_frame.pack(fill="x", pady=2)
        pred_frame.columnconfigure(0, weight=1)
        pred_frame.columnconfigure(1, weight=1)
        
        # Win scenario box
        box_win = tk.Frame(pred_frame, bg="#064e3b", highlightbackground="#10b981", highlightthickness=1, padx=4, pady=3)
        box_win.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        tk.Label(box_win, text="🟢 IF WIN NEXT", bg="#064e3b", fg="#6ee7b7", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.lbl_next_if_win = tk.Label(box_win, text="Trade: $4.82", bg="#064e3b", fg="#ffffff", font=("Segoe UI", 8, "bold"))
        self.lbl_next_if_win.pack(anchor="w")
        self.lbl_bal_if_win = tk.Label(box_win, text="Bal: $64.55", bg="#064e3b", fg="#e2e8f0", font=("Segoe UI", 7))
        self.lbl_bal_if_win.pack(anchor="w")
        
        # Loss scenario box
        box_loss = tk.Frame(pred_frame, bg="#7f1d1d", highlightbackground="#f43f5e", highlightthickness=1, padx=4, pady=3)
        box_loss.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        tk.Label(box_loss, text="🔴 IF LOSS NEXT", bg="#7f1d1d", fg="#fca5a5", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.lbl_next_if_loss = tk.Label(box_loss, text="Trade: $12.53", bg="#7f1d1d", fg="#ffffff", font=("Segoe UI", 8, "bold"))
        self.lbl_next_if_loss.pack(anchor="w")
        self.lbl_bal_if_loss = tk.Label(box_loss, text="Bal: $49.26", bg="#7f1d1d", fg="#e2e8f0", font=("Segoe UI", 7))
        self.lbl_bal_if_loss.pack(anchor="w")
        
        # Action Buttons
        actions_frame = tk.Frame(self.main_container, bg=self.c_bg)
        actions_frame.pack(fill="x", pady=(0, 4))
        actions_frame.columnconfigure(0, weight=5)
        actions_frame.columnconfigure(1, weight=5)
        actions_frame.columnconfigure(2, weight=2)
        
        btn_win = tk.Button(actions_frame, text="WIN [W]", bg=self.c_win, fg="#ffffff", font=("Segoe UI", 10, "bold"),
                            relief="flat", pady=6, command=lambda: self.on_trade('W'))
        btn_win.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        
        btn_loss = tk.Button(actions_frame, text="LOSS [L]", bg=self.c_loss, fg="#ffffff", font=("Segoe UI", 10, "bold"),
                             relief="flat", pady=6, command=lambda: self.on_trade('L'))
        btn_loss.grid(row=0, column=1, sticky="ew", padx=(2, 2))
        
        btn_undo = tk.Button(actions_frame, text="↩", bg="#334155", fg="#ffffff", font=("Segoe UI", 10, "bold"),
                             relief="flat", pady=6, command=self.on_undo)
        btn_undo.grid(row=0, column=2, sticky="ew", padx=(2, 0))
        
        # Stats Card
        self.stats_frame = tk.Frame(self.main_container, bg=self.c_card, padx=6, pady=4)
        self.stats_frame.pack(fill="x", pady=(0, 4))
        
        self.lbl_balance = tk.Label(self.stats_frame, text="Bal: $58.00 | Target: $69.60 (+20.0%)", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 8, "bold"))
        self.lbl_balance.pack(anchor="w")
        
        self.lbl_progress = tk.Label(self.stats_frame, text="Wins: 0/5 | Losses: 0/10", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 7))
        self.lbl_progress.pack(anchor="w")
        
        self.pbar = ttk.Progressbar(self.stats_frame, orient="horizontal", mode="determinate")
        self.pbar.pack(fill="x", pady=(2, 0))
        
        # History Table
        self.history_frame = tk.Frame(self.main_container, bg=self.c_card, padx=4, pady=4)
        self.history_frame.pack(fill="both", expand=True)
        
        tk.Label(self.history_frame, text="📋 Log History", bg=self.c_card, fg=self.c_accent, font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0, 1))
        
        tree_scroll = ttk.Scrollbar(self.history_frame)
        tree_scroll.pack(side="right", fill="y")
        
        columns = ("step", "result", "stake", "pnl", "balance")
        self.tree = ttk.Treeview(self.history_frame, columns=columns, show="headings", height=4, yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.tree.yview)
        
        self.tree.heading("step", text="#")
        self.tree.heading("result", text="Res")
        self.tree.heading("stake", text="Trade")
        self.tree.heading("pnl", text="P&L")
        self.tree.heading("balance", text="Bal")
        
        self.tree.column("step", width=20, anchor="center")
        self.tree.column("result", width=40, anchor="center")
        self.tree.column("stake", width=50, anchor="e")
        self.tree.column("pnl", width=55, anchor="e")
        self.tree.column("balance", width=60, anchor="e")
        
        self.tree.pack(fill="both", expand=True)
        
        # Keybindings
        self.bind("<w>", lambda e: self.on_trade('W'))
        self.bind("<W>", lambda e: self.on_trade('W'))
        self.bind("<l>", lambda e: self.on_trade('L'))
        self.bind("<L>", lambda e: self.on_trade('L'))
        self.bind("<Control-z>", lambda e: self.on_undo())
        
        self.start_session()

    def toggle_sound(self):
        self.sound_enabled = self.chk_sound_var.get()
        
    def toggle_autocopy(self):
        self.auto_copy_enabled = self.chk_copy_var.get()
        
    def toggle_rounding(self):
        if self.engine:
            self.engine.use_exact_round = self.chk_round_var.get()
            self.update_display()

    def on_currency_change(self, event=None):
        val = self.combo_currency.get()
        self.currency_symbol = val
        self.update_display()
        
    def copy_stake_to_clipboard(self):
        if not self.engine:
            return
        rounded_stake, raw_stake, is_done, msg = self.engine.get_next_stake()
        if not is_done:
            stake_to_copy = rounded_stake if self.chk_round_var.get() else f"{raw_stake:.2f}"
            self.clipboard_clear()
            self.clipboard_append(str(stake_to_copy))
            self.btn_copy_stake.config(text="✓", fg="#22c55e")
            self.after(1000, lambda: self.btn_copy_stake.config(text="📋 Copy", fg="#38bdf8"))

    def toggle_topmost(self):
        self.is_topmost = not self.is_topmost
        self.attributes("-topmost", self.is_topmost)
        self.topmost_btn.config(text=f"📌 Top: {'ON' if self.is_topmost else 'OFF'}")
        
    def toggle_compact(self):
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.setup_frame.pack_forget()
            self.history_frame.pack_forget()
            self.stats_frame.pack_forget()
            self.geometry("280x240")
            self.compact_btn.config(text="🗖 Full")
        else:
            self.setup_frame.pack(fill="x", pady=(0, 4))
            self.stats_frame.pack(fill="x", pady=(0, 4))
            self.history_frame.pack(fill="both", expand=True)
            self.geometry("340x550")
            self.compact_btn.config(text="🗖 Mini")

    def start_session(self):
        try:
            cap = float(self.ent_capital.get())
            trades = min(100, max(1, int(self.ent_trades.get())))
            wins = min(trades, max(1, int(self.ent_wins.get())))
            quota_val = float(self.ent_payout.get())
            custom_prof = float(self.ent_profit_pct.get()) if self.ent_profit_pct.get() else None
            use_round = self.chk_round_var.get()
            
            self.engine = ExactExcelMasanielloEngine(cap, trades, wins, quota_val, custom_profit_pct=custom_prof, use_exact_round=use_round)
            self.update_display()
        except ValueError:
            pass

    def on_trade(self, result):
        if not self.engine:
            return
            
        success = self.engine.record_trade(result)
        if success:
            _, wins, losses = self.engine.get_state()
            rounded_stake, raw_stake, is_done, _ = self.engine.get_next_stake()
            
            if is_done:
                if wins >= self.engine.K:
                    self.play_sound("target_win")
                else:
                    self.play_sound("target_loss")
            else:
                if result == 'W':
                    self.play_sound("win")
                else:
                    self.play_sound("loss")
                    
            self.update_display()
            if self.auto_copy_enabled and not is_done and rounded_stake > 0:
                self.copy_stake_to_clipboard()
        else:
            messagebox.showinfo("Session Finished", "This trading session is already complete!")

    def on_undo(self):
        if not self.engine:
            return
        if self.engine.undo_last():
            self.update_display()

    def update_display(self):
        if not self.engine:
            return
            
        curr_balance, wins, losses = self.engine.get_state()
        rounded_stake, raw_stake, is_done, msg = self.engine.get_next_stake()
        pred_win, pred_loss = self.engine.get_win_loss_predictions()
        cs = self.currency_symbol
        use_round = self.chk_round_var.get()
        
        m = wins + losses
        self.lbl_step_info.config(text=f"Trade #{m + 1} of {self.engine.N}" if not is_done else "Session Complete 🎉")
        
        curr_bal_str = f"{int(round(curr_balance))}" if use_round else f"{curr_balance:.2f}"
        target_cap_str = f"{int(round(self.engine.target_capital))}" if use_round else f"{self.engine.target_capital:.2f}"
        
        if is_done:
            if wins >= self.engine.K:
                self.lbl_stake_val.config(text="TARGET WON! 🎉", fg=self.c_win, font=("Segoe UI", 15, "bold"))
                self.lbl_stake_desc.config(text=f"Final Portfolio: {cs}{curr_bal_str} (Target Won!)")
            else:
                self.lbl_stake_val.config(text="TARGET FAILED ❌", fg=self.c_loss, font=("Segoe UI", 15, "bold"))
                self.lbl_stake_desc.config(text=f"Final Portfolio: {cs}{curr_bal_str}")
                
            self.lbl_next_if_win.config(text="Done")
            self.lbl_bal_if_win.config(text=f"Bal: {cs}{curr_bal_str}")
            self.lbl_next_if_loss.config(text="Done")
            self.lbl_bal_if_loss.config(text=f"Bal: {cs}{curr_bal_str}")
        else:
            stake_display = f"{cs}{rounded_stake}" if use_round else f"{cs}{raw_stake:.2f}"
            self.lbl_stake_val.config(text=stake_display, fg=self.c_win if raw_stake > 0 else self.c_subtext, font=("Segoe UI", 20, "bold"))
            self.lbl_stake_desc.config(text=f"👉 SUGGESTED STAKE ({'ROUND' if use_round else 'EXACT EXCEL'})")
            
            if pred_win and pred_loss:
                s_win = f"{cs}{pred_win['next_stake_round']}" if use_round else f"{cs}{pred_win['next_stake_raw']:.2f}"
                b_win = f"{cs}{int(round(pred_win['balance']))}" if use_round else f"{cs}{pred_win['balance']:.2f}"
                self.lbl_next_if_win.config(text=f"Trade: {s_win}" if not pred_win['is_done'] else "Target Won! 🎉")
                self.lbl_bal_if_win.config(text=f"Bal: {b_win}")
                
                s_loss = f"{cs}{pred_loss['next_stake_round']}" if use_round else f"{cs}{pred_loss['next_stake_raw']:.2f}"
                b_loss = f"{cs}{int(round(pred_loss['balance']))}" if use_round else f"{cs}{pred_loss['balance']:.2f}"
                self.lbl_next_if_loss.config(text=f"Trade: {s_loss}" if not pred_loss['is_done'] else "Seq End")
                self.lbl_bal_if_loss.config(text=f"Bal: {b_loss}")

        ret_pct = f"{self.engine.effective_yield_pct:.1f}%"
        self.lbl_balance.config(text=f"Bal: {cs}{curr_bal_str} | Target: {cs}{target_cap_str} (+{ret_pct})")
        self.lbl_progress.config(text=f"Wins: {wins}/{self.engine.K} | Losses: {losses}/{self.engine.N - self.engine.K}")
        
        self.pbar['maximum'] = self.engine.K
        self.pbar['value'] = min(wins, self.engine.K)
        
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for item in self.engine.history:
            res_str = "✅ WIN" if item['result'] == 'W' else "❌ LOSS"
            pnl_val = item['pnl']
            stk_val = item['stake'] if use_round else item['raw_stake']
            bal_val = int(round(item['balance'])) if use_round else item['balance']
            
            stk_str = f"{cs}{stk_val}" if use_round else f"{cs}{stk_val:.2f}"
            bal_str = f"{cs}{bal_val}" if use_round else f"{cs}{bal_val:.2f}"
            pnl_str = f"+{cs}{pnl_val:.2f}" if pnl_val >= 0 else f"-{cs}{abs(pnl_val):.2f}"
            if use_round:
                pnl_str = f"+{cs}{int(round(pnl_val))}" if pnl_val >= 0 else f"-{cs}{abs(int(round(pnl_val)))}"
                
            self.tree.insert("", "end", values=(
                item['step'],
                res_str,
                stk_str,
                pnl_str,
                bal_str
            ))


if __name__ == "__main__":
    app = AegisQuantApp()
    app.mainloop()
