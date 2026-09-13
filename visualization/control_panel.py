import tkinter as tk
from tkinter import ttk

class ControlPanel(ttk.Frame):
    """Control buttons for simulation playback."""
    
    def __init__(self, parent, on_play, on_pause, on_step_forward, on_step_back, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_play = on_play
        self.on_pause = on_pause
        self.on_step_forward = on_step_forward
        self.on_step_back = on_step_back
        
        self.is_playing = False
        
        # Control buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.play_btn = ttk.Button(
            button_frame, text="▶ Play", command=self._handle_play
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(
            button_frame, text="⏸ Pause", command=self._handle_pause, state=tk.DISABLED
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, text="⏮ Back", command=on_step_back
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, text="⏭ Next", command=on_step_forward
        ).pack(side=tk.LEFT, padx=5)
        
        # Step counter
        step_frame = ttk.Frame(self)
        step_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        ttk.Label(step_frame, text="Step:").pack(side=tk.LEFT, padx=5)
        self.step_label = ttk.Label(
            step_frame, text="0/0", font=("Courier", 12, "bold")
        )
        self.step_label.pack(side=tk.LEFT, padx=5)
    
    def _handle_play(self):
        self.is_playing = True
        self.play_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.on_play()
    
    def _handle_pause(self):
        self.is_playing = False
        self.play_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.on_pause()
    
    def update_step_display(self, current: int, total: int):
        self.step_label.config(text=f"{current}/{total}")
    
    def stop_playback(self):
        """Called when playback reaches the end."""
        self.is_playing = False
        self.play_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)