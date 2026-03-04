"""
Windows CAPTCHA Terminal Tool - Dark USB Theme
==============================================

Dark themed CAPTCHA with USB pendrive icon and unique neon colors.

Usage:
    python captcha.py
    
In your Python code:
    from captcha import show_captcha
    
    if show_captcha():
        print("User verified!")
    else:
        print("Verification cancelled")
"""

import tkinter as tk
from tkinter import messagebox
import sys
import math
import time

class AnimatedCheckmark:
    def __init__(self, canvas, x, y, size=40, color='#00ff88'):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.progress = 0
        
    def draw_checkmark(self):
        """Draw animated checkmark with neon green"""
        self.canvas.delete('checkmark')
        
        if self.progress == 0:
            return
        
        x, y = self.x, self.y
        size = self.size
        
        # Down stroke (70% of animation)
        if self.progress <= 0.7:
            progress_down = self.progress / 0.7
            x1, y1 = x - size * 0.2, y - size * 0.1
            x2, y2 = x - size * 0.15, y + size * 0.35
            
            x_end = x1 + (x2 - x1) * progress_down
            y_end = y1 + (y2 - y1) * progress_down
            
            self.canvas.create_line(x1, y1, x_end, y_end, 
                                   fill=self.color, width=5, capstyle=tk.ROUND,
                                   tags='checkmark')
        else:
            # Draw full down stroke
            x1, y1 = x - size * 0.2, y - size * 0.1
            x2, y2 = x - size * 0.15, y + size * 0.35
            self.canvas.create_line(x1, y1, x2, y2, 
                                   fill=self.color, width=5, capstyle=tk.ROUND,
                                   tags='checkmark')
            
            # Up stroke (30% of animation)
            progress_up = (self.progress - 0.7) / 0.3
            x3, y3 = x + size * 0.35, y - size * 0.25
            
            x_end = x2 + (x3 - x2) * progress_up
            y_end = y2 + (y3 - y2) * progress_up
            
            self.canvas.create_line(x2, y2, x_end, y_end, 
                                   fill=self.color, width=5, capstyle=tk.ROUND,
                                   tags='checkmark')
    
    def animate(self):
        """Animate the checkmark"""
        if self.progress < 1:
            self.progress += 0.08
            self.draw_checkmark()
            self.canvas.after(30, self.animate)
        else:
            self.draw_checkmark()
    
    def start(self):
        """Start checkmark animation"""
        self.progress = 0
        self.animate()


class AnimatedSpinner:
    def __init__(self, canvas, x, y, size=20, color='#ff006e'):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.angle = 0
        self.running = False
        
    def draw_spinner(self):
        """Draw animated spinner with neon colors"""
        self.canvas.delete('spinner')
        
        cx, cy = self.x, self.y
        
        # Draw outer circle (dark)
        self.canvas.create_oval(
            cx - self.size - 3, cy - self.size - 3,
            cx + self.size + 3, cy + self.size + 3,
            outline='#333333', width=2, tags='spinner'
        )
        
        # Draw rotating arc with gradient effect
        start_angle = self.angle
        extent = 100
        
        # Create smooth arc
        num_points = 25
        points = []
        for i in range(num_points + 1):
            angle = start_angle + (extent * i / num_points)
            rad = math.radians(angle)
            x = cx + self.size * math.cos(rad)
            y = cy + self.size * math.sin(rad)
            points.append((x, y))
        
        if len(points) > 1:
            self.canvas.create_line(points, fill=self.color, width=3, 
                                   capstyle=tk.ROUND, tags='spinner', smooth=True)
    
    def start(self):
        """Start spinner animation"""
        self.running = True
        self.animate()
    
    def animate(self):
        """Animation loop"""
        if self.running:
            self.angle = (self.angle + 10) % 360
            self.draw_spinner()
            self.canvas.after(40, self.animate)
    
    def stop(self):
        """Stop spinner animation"""
        self.running = False
        self.canvas.delete('spinner')


class DarkUSBCAPTCHA:
    def __init__(self, root, timeout=10):
        self.root = root
        self.timeout = timeout
        self.time_remaining = timeout
        self.timer_running = False
        self.root.title("Security Verification")
        self.root.geometry("600x320")
        self.root.resizable(False, False)
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        self.verified = False
        self.checkbox_state = tk.BooleanVar()
        self.verification_in_progress = False
        self.verification_complete = False
        
        # Dark unique color scheme
        self.bg_primary = '#0a0e27'        # Deep dark blue
        self.bg_secondary = '#1a1f3a'      # Dark blue
        self.border_color = '#2d3561'      # Medium dark blue
        self.text_primary = '#e0e6ff'      # Light blue white
        self.text_secondary = '#8892b0'    # Medium blue gray
        self.accent_neon_green = '#00ff88' # Neon green
        self.accent_neon_pink = '#ff006e'  # Neon pink
        self.accent_purple = '#b537f2'     # Purple
        self.accent_cyan = '#00d9ff'       # Cyan
        
        # Configure root window
        self.root.configure(bg=self.bg_primary)
        
        # Header with custom styling
        header_frame = tk.Frame(self.root, bg=self.bg_secondary, height=50)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Header content
        header_content = tk.Frame(header_frame, bg=self.bg_secondary)
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)
        
        # USB icon in header
        usb_label = tk.Label(header_content, text="🔐", 
                           font=('Arial', 16),
                           bg=self.bg_secondary, fg=self.accent_neon_green)
        usb_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Title
        title_label = tk.Label(header_content, text="Security Verification", 
                             font=('Segoe UI', 12, 'bold'),
                             bg=self.bg_secondary, fg=self.text_primary)
        title_label.pack(side=tk.LEFT)
        
        # Gradient divider
        divider_frame = tk.Frame(self.root, bg=self.bg_primary, height=2)
        divider_frame.pack(fill=tk.X)
        divider = tk.Frame(divider_frame, bg=self.accent_neon_pink, height=2)
        divider.pack(fill=tk.X)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg=self.bg_primary)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        
        # STATE 1: Unchecked checkbox
        self.checkbox_frame = tk.Frame(main_frame, bg=self.bg_primary)
        self.checkbox_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left section - Checkbox
        left_section = tk.Frame(self.checkbox_frame, bg=self.bg_primary)
        left_section.pack(side=tk.LEFT, padx=(0, 32))
        
        # Custom checkbox with dark styling
        self.checkbox_container = tk.Frame(left_section, bg=self.bg_primary)
        self.checkbox_container.pack()
        
        self.checkbox_visual = tk.Canvas(self.checkbox_container, width=75, height=75,
                                        bg=self.bg_primary, highlightthickness=0,
                                        cursor='hand2')
        self.checkbox_visual.pack()
        
        # Draw unchecked checkbox with border glow
        self.checkbox_rect = self.checkbox_visual.create_rectangle(
            8, 8, 67, 67, fill=self.bg_secondary, outline=self.accent_cyan, width=2
        )
        
        # Bind hover effects
        self.checkbox_visual.bind('<Enter>', self.on_checkbox_hover)
        self.checkbox_visual.bind('<Leave>', self.on_checkbox_leave)
        self.checkbox_visual.bind('<Button-1>', self.on_checkbox_click)
        
        # Checkmark canvas (will be animated)
        self.checkmark_container = tk.Canvas(self.checkbox_container, width=75, height=75,
                                            bg=self.bg_primary, highlightthickness=0)
        self.checkmark_container.pack(side=tk.LEFT, padx=0)
        self.checkmark_container.place_forget()
        
        self.checkmark_animator = AnimatedCheckmark(self.checkmark_container, 37, 37, 
                                                   size=24, color=self.accent_neon_green)
        
        # Middle section - Text
        middle_section = tk.Frame(self.checkbox_frame, bg=self.bg_primary)
        middle_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_label = tk.Label(middle_section, text="Verify Your Identity",
                              font=('Segoe UI', 22, 'bold'),
                              bg=self.bg_primary, fg=self.text_primary)
        title_label.pack(anchor='w', pady=(0, 8))
        
        subtitle_label = tk.Label(middle_section, text="Click the checkbox to verify using USB device",
                                 font=('Segoe UI', 10),
                                 bg=self.bg_primary, fg=self.text_secondary)
        subtitle_label.pack(anchor='w', pady=(0, 12))
        
        links_label = tk.Label(middle_section, text="Privacy • Security • Help",
                              font=('Segoe UI', 9),
                              bg=self.bg_primary, fg=self.accent_cyan)
        links_label.pack(anchor='w', pady=(0, 8))
        
        # Timer label
        self.timer_label = tk.Label(middle_section, text=f"⏱️ Time remaining: {self.timeout}s",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.bg_primary, fg=self.accent_neon_pink)
        self.timer_label.pack(anchor='w', pady=(0, 0))
        
        # Right section - USB Icon
        right_section = tk.Frame(self.checkbox_frame, bg=self.bg_primary)
        right_section.pack(side=tk.LEFT, padx=(32, 0))
        
        self.usb_canvas = tk.Canvas(right_section, width=80, height=80,
                                   bg=self.bg_primary, highlightthickness=0)
        self.usb_canvas.pack()
        
        # Draw USB pendrive icon
        self.draw_usb_icon()
        
        self.spinner = AnimatedSpinner(self.usb_canvas, 40, 40, size=16, color=self.accent_neon_pink)
        
        # STATE 2: Verified state
        self.verified_frame = tk.Frame(main_frame, bg=self.bg_primary)
        
        # Verified left section
        verified_left = tk.Frame(self.verified_frame, bg=self.bg_primary)
        verified_left.pack(side=tk.LEFT, padx=(0, 32))
        
        self.verified_checkbox_canvas = tk.Canvas(verified_left, width=75, height=75,
                                                 bg=self.bg_primary, highlightthickness=0)
        self.verified_checkbox_canvas.pack()
        
        # Checked checkbox with gradient background
        self.verified_checkbox_canvas.create_rectangle(
            8, 8, 67, 67, fill=self.accent_neon_green, outline=self.accent_neon_green, width=2
        )
        
        # Add glow effect
        self.verified_checkbox_canvas.create_rectangle(
            5, 5, 70, 70, fill='', outline=self.accent_purple, width=1
        )
        
        # Checkmark will be animated
        self.verified_checkmark = AnimatedCheckmark(self.verified_checkbox_canvas, 37, 37, 
                                                   size=24, color=self.bg_primary)
        
        # Verified middle section
        verified_middle = tk.Frame(self.verified_frame, bg=self.bg_primary)
        verified_middle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        verified_title = tk.Label(verified_middle, text="Verify Your Identity",
                                 font=('Segoe UI', 22, 'bold'),
                                 bg=self.bg_primary, fg=self.text_primary)
        verified_title.pack(anchor='w', pady=(0, 8))
        
        verified_status = tk.Label(verified_middle, text="Click the checkbox to verify using USB device",
                                  font=('Segoe UI', 10),
                                  bg=self.bg_primary, fg=self.text_secondary)
        verified_status.pack(anchor='w', pady=(0, 12))
        
        verified_check = tk.Label(verified_middle, text="✓ USB Device Verified",
                                 font=('Segoe UI', 11, 'bold'),
                                 bg=self.bg_primary, fg=self.accent_neon_green)
        verified_check.pack(anchor='w', pady=(0, 0))
        
        # Verified right section
        verified_right = tk.Frame(self.verified_frame, bg=self.bg_primary)
        verified_right.pack(side=tk.LEFT, padx=(32, 0))
        
        self.verified_usb_canvas = tk.Canvas(verified_right, width=80, height=80,
                                            bg=self.bg_primary, highlightthickness=0)
        self.verified_usb_canvas.pack()
        
        # Draw verified USB icon
        self.draw_verified_usb_icon()
        
        # Bottom section - Buttons
        button_frame = tk.Frame(self.root, bg=self.bg_primary)
        button_frame.pack(fill=tk.X, padx=24, pady=(0, 16), side=tk.BOTTOM)
        
        # Cancel button
        self.cancel_btn = tk.Button(button_frame, text="Cancel",
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=self.bg_secondary, fg=self.text_secondary,
                                   relief=tk.FLAT, bd=0,
                                   padx=20, pady=8,
                                   command=self.on_cancel,
                                   activebackground=self.border_color,
                                   activeforeground=self.accent_cyan)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))
        
        # Verify button
        self.verify_btn = tk.Button(button_frame, text="Verify",
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=self.accent_neon_green, fg=self.bg_primary,
                                   relief=tk.FLAT, bd=0,
                                   padx=20, pady=8,
                                   command=self.on_verify,
                                   activebackground=self.accent_cyan,
                                   activeforeground=self.bg_primary)
        self.verify_btn.pack(side=tk.RIGHT)
        self.verify_btn.pack_forget()  # Hide initially
        
        # Prevent window from closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # Start countdown timer
        self.timer_running = True
        self.update_timer()
    
    def draw_usb_icon(self):
        """Draw USB pendrive icon"""
        self.usb_canvas.delete('usb')
        
        cx, cy = 40, 40
        
        # USB connector top (metal part)
        self.usb_canvas.create_rectangle(
            cx - 8, cy - 20, cx + 8, cy - 12,
            fill=self.accent_cyan, outline=self.accent_purple, width=1, tags='usb'
        )
        
        # USB body (pendrive)
        self.usb_canvas.create_rectangle(
            cx - 12, cy - 8, cx + 12, cy + 15,
            fill=self.accent_neon_pink, outline=self.accent_neon_pink, 
            width=2, tags='usb'
        )
        
        # USB highlight/shine
        self.usb_canvas.create_rectangle(
            cx - 10, cy - 6, cx - 6, cy + 10,
            fill='', outline=self.accent_cyan, width=1, tags='usb'
        )
    
    def draw_verified_usb_icon(self):
        """Draw verified USB icon with checkmark"""
        self.verified_usb_canvas.delete('verified_usb')
        
        cx, cy = 40, 40
        
        # USB connector top
        self.verified_usb_canvas.create_rectangle(
            cx - 8, cy - 20, cx + 8, cy - 12,
            fill=self.accent_cyan, outline=self.accent_neon_green, width=2, 
            tags='verified_usb'
        )
        
        # USB body
        self.verified_usb_canvas.create_rectangle(
            cx - 12, cy - 8, cx + 12, cy + 15,
            fill=self.accent_neon_green, outline=self.accent_neon_green, 
            width=2, tags='verified_usb'
        )
        
        # Checkmark on USB
        self.verified_usb_canvas.create_text(
            cx, cy + 4, text='✓', font=('Arial', 20, 'bold'),
            fill=self.bg_primary, tags='verified_usb'
        )
    
    def on_checkbox_hover(self, event=None):
        """Handle checkbox hover"""
        if not self.verification_in_progress:
            self.checkbox_visual.itemconfig(self.checkbox_rect, outline=self.accent_neon_green)
    
    def on_checkbox_leave(self, event=None):
        """Handle checkbox leave"""
        if not self.verification_in_progress:
            self.checkbox_visual.itemconfig(self.checkbox_rect, outline=self.accent_cyan)
    
    def on_checkbox_click(self, event=None):
        """Handle checkbox click"""
        if not self.checkbox_state.get() and not self.verification_in_progress:
            self.checkbox_state.set(True)
            self.verification_in_progress = True
            
            # Animate checkbox color change
            self.checkbox_visual.itemconfig(self.checkbox_rect, fill=self.accent_neon_green)
            self.checkbox_visual.itemconfig(self.checkbox_rect, outline=self.accent_neon_green)
            
            # Show checkmark animation
            self.checkmark_container.place(in_=self.checkbox_container, x=0, y=0)
            self.checkmark_animator.start()
            
            # Start spinner animation
            self.spinner.start()
            
            # Simulate verification (2-3 seconds)
            delay = 2000 + int((time.time() * 1000) % 1000)
            self.root.after(delay, self.complete_verification)
    
    def complete_verification(self):
        """Mark verification as complete with animation"""
        self.verification_complete = True
        self.spinner.stop()
        
        # Smooth transition to verified state
        self.checkbox_frame.pack_forget()
        
        # Small delay for smooth transition
        self.root.after(200, lambda: (
            self.verified_frame.pack(fill=tk.BOTH, expand=True),
            self.verified_checkmark.start(),
            self.verify_btn.pack(side=tk.RIGHT)
        ))
    
    def on_verify(self):
        """Handle verification completion"""
        if self.verification_complete:
            self.verified = True
            messagebox.showinfo("Success", "✓ USB Device Verified Successfully!")
            self.root.destroy()
    
    def on_cancel(self):
        """Handle cancellation"""
        if messagebox.askyesno("Cancel", "Cancel verification?"):
            self.spinner.stop()
            self.verified = False
            self.root.destroy()
    
    def is_verified(self):
        return self.verified
    
    def update_timer(self):
        """Update countdown timer"""
        if not self.timer_running:
            return
        
        if self.time_remaining > 0:
            self.timer_label.config(text=f"⏱️ Time remaining: {self.time_remaining}s")
            self.time_remaining -= 1
            self.root.after(1000, self.update_timer)
        else:
            # Timeout expired - auto-close and block device
            self.timer_label.config(text="⏱️ Time expired - Device BLOCKED")
            self.timer_running = False
            self.verified = False
            self.spinner.stop()
            self.root.after(1500, self.root.destroy)


def show_captcha(timeout=10):
    """
    Display the dark USB themed CAPTCHA verification window
    
    Args:
        timeout: Time in seconds before auto-closing (default 10)
    
    Returns:
        bool: True if user verified successfully, False otherwise (timeout or cancel)
    """
    root = tk.Tk()
    app = DarkUSBCAPTCHA(root, timeout=timeout)
    root.mainloop()
    return app.is_verified()


if __name__ == "__main__":
    print("[*] Launching CAPTCHA verification window...")
    result = show_captcha()
    
    if result:
        print("[✓] Verification passed!")
        sys.exit(0)
    else:
        print("[✗] Verification cancelled!")
        sys.exit(1)