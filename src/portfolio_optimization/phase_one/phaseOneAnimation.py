import sys
import time
import math
import random
import threading
import itertools

class Colors:
    """Terminal styling codes for colorful output"""
    LIGHT_BLUE = '\033[94m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'
    CYAN = '\033[96m'

class AnimationController:
    """Controls the display of animated loading indicators for research functions"""
    
    def __init__(self, analysis_steps=None, title="AI Research in Progress", animation_type="matrix"):
        """Initialize the animation controller with customizable steps and title
        
        Args:
            analysis_steps (list): List of analysis steps to display during animation
            title (str): Title to display at the top of the animation
            animation_type (str): Type of animation to display ("matrix", "sift", "rocket", "elegant")
        """
        # Default steps if none provided
        self.analysis_steps = analysis_steps or [
            "Analyzing market data trends",
            "Processing financial metrics",
            "Evaluating investment opportunities",
            "Calculating risk-adjusted returns",
            "Examining market volatility patterns",
            "Reviewing sector performance metrics",
            "Assessing macroeconomic indicators",
            "Evaluating company fundamentals",
            "Analyzing technical indicators",
            "Calculating correlation coefficients",
            "Reviewing earnings projections",
            "Examining global market trends"
        ]
        self.title = title
        self.animation_running = False
        self.animation_thread = None
        self.animation_type = animation_type
        
    def start(self):
        """Start the animation in a background thread"""
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self._display_animation)
        self.animation_thread.daemon = True  # Make thread terminate when main program exits
        self.animation_thread.start()
        return self
        
    def stop(self):
        """Stop the animation and clean up resources"""
        if self.animation_running:
            self.animation_running = False
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join(timeout=1.0)  # Wait for clean termination with timeout
                time.sleep(0.1)  # Small pause to ensure cleanup completes
        
    def _display_animation(self):
        """Main animation display function"""
        if self.animation_type == "matrix":
            self._display_matrix_animation()
        elif self.animation_type == "sift":
            self._display_data_sift_animation()
        elif self.animation_type == "rocket":
            self._display_rocket_animation()
        elif self.animation_type == "elegant":
            self._display_elegant_animation()
        else:
            self._display_matrix_animation()  # Default to matrix
    
    def _display_matrix_animation(self):
        """Display the matrix-style data stream animation"""
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        step_index = 0
        step_change_time = time.time() + 2  # Change analysis step every 2 seconds
        dots_cycle_time = time.time() + 0.4  # Update dots every 0.4 seconds
        dots_index = 0  # For cycling through dots
        
        # Matrix data stream parameters
        DATA_WIDTH = 30  # Total width of the data stream area
        NUM_COLUMNS = 15  # Increased number of columns to fill width better
        column_heights = [0] * NUM_COLUMNS  # Current height of each column
        column_phases = [random.uniform(0, 2 * 3.14159) for _ in range(NUM_COLUMNS)]  # Random starting phases
        column_speeds = [random.uniform(0.2, 0.5) for _ in range(NUM_COLUMNS)]  # Different speeds for each column
        
        # Characters to represent different heights
        DATA_CHARS = " ▁▂▃▄▅▆▇█"  # Ordered by height, first is empty
        
        # Color gradient for the stream
        COLORS = [
            Colors.LIGHT_BLUE,
            Colors.WHITE,
            Colors.LIGHT_BLUE,
            Colors.WHITE,
            Colors.LIGHT_BLUE
        ]
        
        # Left and right borders
        LEFT_BRACKET = '┃'
        RIGHT_BRACKET = '┃'
        
        # Animation timing
        last_update = time.time()
        
        # Dots for processing message
        dot_states = ["", ".", "..", "..."]
        
        # Hide cursor
        sys.stdout.write('\033[?25l')
        
        # Print exact number of lines needed without extra spacing
        # Just create empty space for the 3 animation lines without extra newlines
        print("", end="")  # No extra newlines
        
        # We need exactly 3 lines for our animation
        sys.stdout.write("\n\n\n")
        
        # Move cursor up 3 lines to the start position
        sys.stdout.write('\033[3A')
        sys.stdout.flush()
        
        try:
            while self.animation_running:
                current_time = time.time()
                elapsed = current_time - last_update
                last_update = current_time
                
                # Update analysis step periodically
                if current_time > step_change_time:
                    step_index = (step_index + 1) % len(self.analysis_steps)
                    step_change_time = current_time + 2
                
                # Update dots animation
                if current_time > dots_cycle_time:
                    dots_index = (dots_index + 1) % len(dot_states)
                    dots_cycle_time = current_time + 0.4
                
                # Update column heights based on sine waves with different phases and speeds
                for i in range(NUM_COLUMNS):
                    # Update the phase for this column
                    column_phases[i] += column_speeds[i] * elapsed * 10
                    
                    # Calculate height using sine wave (0-8 range for our characters)
                    column_heights[i] = 4 + 3.5 * math.sin(column_phases[i])
                
                # Start at the first line position
                sys.stdout.write('\r')
                
                # Line 1: Spinner with title
                spin_char = next(spinner)
                sys.stdout.write(f"{Colors.BOLD}{Colors.LIGHT_BLUE}{self.title} {spin_char}{Colors.END}\033[K\n")
                
                # Line 2: Current analysis step
                sys.stdout.write(f"{Colors.WHITE}{self.analysis_steps[step_index]}{Colors.END}\033[K\n")
                
                # Line 3: Matrix Data Stream visualization
                data_stream = []
                for i in range(NUM_COLUMNS):
                    # Get the character based on column height
                    height_index = min(int(column_heights[i]), len(DATA_CHARS) - 1)
                    char = DATA_CHARS[height_index]
                    
                    # Determine color based on height for a gradient effect
                    color_index = min(int(column_heights[i] / 2), len(COLORS) - 1)
                    color = COLORS[color_index]
                    
                    # Add the colored character - make it exactly 2 chars wide for consistent width
                    data_stream.append(f"{color}{char * 2}{Colors.END}")
                
                # Join all columns and format with brackets (no padding needed since we're filling the width)
                data_display = ''.join(data_stream)
                
                # Add animated dots to "Processing data"
                processing_text = f"Processing data{dot_states[dots_index]}"
                
                sys.stdout.write(f"{LEFT_BRACKET}{data_display}{RIGHT_BRACKET} {processing_text}\033[K")
                
                # Reset cursor position to beginning
                sys.stdout.write('\033[2A\r')
                sys.stdout.flush()
                time.sleep(0.05)  # Faster update for smoother animation
            
            # Carefully clean up just the animation lines
            # Go to the beginning of the animation area
            sys.stdout.write('\r')
            
            # Clear each of the 3 animation lines individually
            for _ in range(3):
                sys.stdout.write('\033[K')  # Clear current line
                sys.stdout.write('\n')      # Move to next line
            
            # Move back up to the beginning of where animation was
            sys.stdout.write('\033[3A')
            sys.stdout.flush()
            
        finally:
            # Always ensure cursor is shown again, even if there's an exception
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()

    def _display_data_sift_animation(self):
        """Display a data sifting animation for search visualization"""
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        step_index = 0
        step_change_time = time.time() + 2
        dots_cycle_time = time.time() + 0.4
        dots_index = 0
        
        # Data sifting parameters
        STREAM_WIDTH = 30
        data_stream = []
        
        # Generate random data pieces with different statuses
        for _ in range(STREAM_WIDTH):
            status = random.choice(['pending', 'filtered', 'matched'])
            data_stream.append({
                'status': status,
                'position': random.random(),  # for movement
                'speed': random.uniform(0.05, 0.2)
            })
        
        # Left and right borders
        LEFT_BRACKET = '┃'
        RIGHT_BRACKET = '┃'
        
        # Animation timing
        last_update = time.time()
        filter_change_time = time.time() + 1.5  # Change filter pattern periodically
        
        # Dots for search message
        dot_states = ["", ".", "..", "..."]
        
        # Data symbols
        symbols = {
            'pending': '○',   # Not yet processed
            'filtered': '○',  # Also use circle but different color
            'matched': '●'    # Matched search criteria
        }
        
        # Symbol colors - using only light blue and white
        colors = {
            'pending': Colors.WHITE,
            'filtered': Colors.LIGHT_BLUE,
            'matched': Colors.WHITE
        }
        
        # Hide cursor
        sys.stdout.write('\033[?25l')
        
        # Create space for animation
        sys.stdout.write("\n\n\n")
        sys.stdout.write('\033[3A')
        sys.stdout.flush()
        
        try:
            while self.animation_running:
                current_time = time.time()
                elapsed = current_time - last_update
                last_update = current_time
                
                # Update analysis step periodically
                if current_time > step_change_time:
                    step_index = (step_index + 1) % len(self.analysis_steps)
                    step_change_time = current_time + 2
                
                # Update dots animation
                if current_time > dots_cycle_time:
                    dots_index = (dots_index + 1) % len(dot_states)
                    dots_cycle_time = current_time + 0.4
                
                # Update filter pattern periodically
                if current_time > filter_change_time:
                    filter_change_time = current_time + 1.5
                    
                    # Randomly change the status of some data
                    for i in range(STREAM_WIDTH):
                        if random.random() < 0.3:  # 30% chance to change
                            data_stream[i]['status'] = random.choice(['pending', 'filtered', 'matched'])
                
                # Update data positions
                for i in range(STREAM_WIDTH):
                    data = data_stream[i]
                    data['position'] += data['speed'] * elapsed
                    if data['position'] > 1:
                        data['position'] -= 1
                        # Chance to change status when looping
                        if random.random() < 0.5:
                            data['status'] = random.choice(['pending', 'filtered', 'matched'])
                            data['speed'] = random.uniform(0.05, 0.2)
                
                # Sort by position for visual flow
                data_stream.sort(key=lambda x: x['position'])
                
                # Start at the first line position
                sys.stdout.write('\r')
                
                # Line 1: Spinner with title
                spin_char = next(spinner)
                sys.stdout.write(f"{Colors.BOLD}{Colors.LIGHT_BLUE}{self.title} {spin_char}{Colors.END}\033[K\n")
                
                # Line 2: Current analysis step
                sys.stdout.write(f"{Colors.WHITE}{self.analysis_steps[step_index]}{Colors.END}\033[K\n")
                
                # Line 3: Data sift visualization
                stream_display = []
                for data in data_stream:
                    color = colors[data['status']]
                    symbol = symbols[data['status']]
                    stream_display.append(f"{color}{symbol}{Colors.END}")
                
                # Join and display
                stream_str = ''.join(stream_display)
                
                # Show processing text with animated dots
                processing_text = f"Processing{dot_states[dots_index]}"
                
                sys.stdout.write(f"{LEFT_BRACKET}{stream_str}{RIGHT_BRACKET} {processing_text}\033[K")
                
                # Reset cursor position to beginning
                sys.stdout.write('\033[2A\r')
                sys.stdout.flush()
                time.sleep(0.05)
                
        finally:
            # Clean up
            sys.stdout.write('\r')
            for _ in range(3):
                sys.stdout.write('\033[K')
                sys.stdout.write('\n')
            sys.stdout.write('\033[3A')
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()

    def _display_rocket_animation(self):
        """Display a satellite moving randomly around the screen"""
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        step_index = 0
        step_change_time = time.time() + 2
        dots_cycle_time = time.time() + 0.4
        dots_index = 0
        
        # Display parameters
        DISPLAY_WIDTH = 30
        
        # Satellite parameters
        satellite_x = DISPLAY_WIDTH // 2  # Start in the middle
        satellite_y = 0  # Only need x since we're in a single line
        
        # Direction and movement
        dx = random.choice([-1, 1])  # Initial direction
        position_change_time = time.time()
        direction_change_time = time.time() + 1.0  # Change direction randomly
        
        # Satellite emoji
        satellite_symbol = "🛰️"
        
        # Background stars (for space feeling) - simple dots
        star_positions = []
        for _ in range(15):  # More stars but simpler
            star_positions.append(random.randint(0, DISPLAY_WIDTH-1))
        
        # Left and right borders
        LEFT_BRACKET = '┃'
        RIGHT_BRACKET = '┃'
        
        # Animation timing
        last_update = time.time()
        
        # Dots for processing message
        dot_states = ["", ".", "..", "..."]
        
        # Hide cursor
        sys.stdout.write('\033[?25l')
        
        # Create space for animation
        sys.stdout.write("\n\n\n")
        sys.stdout.write('\033[3A')
        sys.stdout.flush()
        
        try:
            while self.animation_running:
                current_time = time.time()
                elapsed = current_time - last_update
                last_update = current_time
                
                # Update analysis step periodically
                if current_time > step_change_time:
                    step_index = (step_index + 1) % len(self.analysis_steps)
                    step_change_time = current_time + 2
                
                # Update dots animation
                if current_time > dots_cycle_time:
                    dots_index = (dots_index + 1) % len(dot_states)
                    dots_cycle_time = current_time + 0.4
                
                # Randomly change direction
                if current_time > direction_change_time:
                    dx = random.choice([-1, 0, 1])  # Can go left, right, or stay still
                    if dx == 0:  # If staying still, set a shorter time before next direction change
                        direction_change_time = current_time + 0.5
                    else:
                        direction_change_time = current_time + random.uniform(0.8, 2.0)
                
                # Update satellite position
                if current_time > position_change_time:
                    position_change_time = current_time + 0.1  # Move every 0.1 seconds
                    
                    # Move the satellite
                    satellite_x += dx
                    
                    # Wrap around if out of bounds
                    if satellite_x < 0:
                        satellite_x = DISPLAY_WIDTH - 1
                    elif satellite_x >= DISPLAY_WIDTH:
                        satellite_x = 0
                
                # Start at the first line position
                sys.stdout.write('\r')
                
                # Line 1: Spinner with title
                spin_char = next(spinner)
                sys.stdout.write(f"{Colors.BOLD}{Colors.LIGHT_BLUE}{self.title} {spin_char}{Colors.END}\033[K\n")
                
                # Line 2: Current analysis step
                sys.stdout.write(f"{Colors.WHITE}{self.analysis_steps[step_index]}{Colors.END}\033[K\n")
                
                # Line 3: Satellite visualization
                display = [' '] * DISPLAY_WIDTH
                
                # Draw stars in background (space feeling) - just simple dots
                for star_pos in star_positions:
                    if not (satellite_x <= star_pos < satellite_x + len(satellite_symbol)):  # Don't draw stars where the satellite is
                        color = Colors.LIGHT_BLUE if random.random() > 0.7 else Colors.WHITE
                        display[star_pos] = f"{color}·{Colors.END}"
                
                # Draw the satellite
                if 0 <= satellite_x < DISPLAY_WIDTH:
                    display[satellite_x] = f"{Colors.WHITE}{satellite_symbol}{Colors.END}"
                
                # Join and display
                display_str = ''.join(display)
                
                # Add animated dots to "Processing"
                processing_text = f"Processing{dot_states[dots_index]}"
                
                sys.stdout.write(f"{LEFT_BRACKET}{display_str}{RIGHT_BRACKET} {processing_text}\033[K")
                
                # Reset cursor position to beginning
                sys.stdout.write('\033[2A\r')
                sys.stdout.flush()
                time.sleep(0.05)
                
        finally:
            # Clean up
            sys.stdout.write('\r')
            for _ in range(3):
                sys.stdout.write('\033[K')
                sys.stdout.write('\n')
            sys.stdout.write('\033[3A')
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()

    def _display_elegant_animation(self):
        """Display a chic, minimalist animation with a refined aesthetic for client-facing interfaces"""
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        step_index = 0
        step_change_time = time.time() + 2
        dots_cycle_time = time.time() + 0.4
        dots_index = 0
        
        # Display parameters
        DISPLAY_WIDTH = 30
        
        # Progress bar parameters
        progress = 0
        progress_direction = 1  # 1 for increasing, -1 for decreasing
        progress_speed = 0.05
        
        # Refined symbols
        bar_empty = "─"
        bar_full = "━"
        accent = "│"
        
        # Elegant color palette
        primary_color = Colors.LIGHT_BLUE
        secondary_color = Colors.WHITE
        accent_color = Colors.CYAN
        
        # Left and right borders
        LEFT_BRACKET = '┃'
        RIGHT_BRACKET = '┃'
        
        # Animation timing
        last_update = time.time()
        progress_update_time = time.time()
        
        # Status message with animated dots
        status_messages = ["Processing", "Please wait"]
        status_index = 0
        status_change_time = time.time() + 3
        
        # Ellipsis animation
        dot_states = ["", ".", "..", "..."]
        
        # Hide cursor
        sys.stdout.write('\033[?25l')
        
        # Create space for animation
        sys.stdout.write("\n\n\n")
        sys.stdout.write('\033[3A')
        sys.stdout.flush()
        
        try:
            while self.animation_running:
                current_time = time.time()
                elapsed = current_time - last_update
                last_update = current_time
                
                # Update analysis step periodically
                if current_time > step_change_time:
                    step_index = (step_index + 1) % len(self.analysis_steps)
                    step_change_time = current_time + 2
                
                # Update dots animation
                if current_time > dots_cycle_time:
                    dots_index = (dots_index + 1) % len(dot_states)
                    dots_cycle_time = current_time + 0.4
                
                # Update status message
                if current_time > status_change_time:
                    status_index = (status_index + 1) % len(status_messages)
                    status_change_time = current_time + 3
                
                # Update progress bar
                if current_time > progress_update_time:
                    progress += progress_direction * progress_speed
                    
                    # Reverse direction at the edges
                    if progress >= 1.0:
                        progress = 1.0
                        progress_direction = -1
                    elif progress <= 0.0:
                        progress = 0.0
                        progress_direction = 1
                        
                    progress_update_time = current_time + 0.05  # Smooth animation
                
                # Start at the first line position
                sys.stdout.write('\r')
                
                # Line 1: Spinner with title
                spin_char = next(spinner)
                sys.stdout.write(f"{Colors.BOLD}{primary_color}{self.title} {spin_char}{Colors.END}\033[K\n")
                
                # Line 2: Current analysis step
                sys.stdout.write(f"{secondary_color}{self.analysis_steps[step_index]}{Colors.END}\033[K\n")
                
                # Line 3: Progress bar visualization
                display = []
                
                # Calculate filled portion of the bar
                filled_width = int(DISPLAY_WIDTH * progress)
                
                # Position for accent marker
                accent_pos = min(filled_width, DISPLAY_WIDTH - 1)
                
                # Build the bar
                for i in range(DISPLAY_WIDTH):
                    if i < filled_width:
                        # Filled part
                        char = f"{primary_color}{bar_full}{Colors.END}"
                    else:
                        # Empty part
                        char = f"{Colors.WHITE}{bar_empty}{Colors.END}"
                    
                    # Add accent marker at progress point
                    if i == accent_pos:
                        char = f"{accent_color}{accent}{Colors.END}"
                        
                    display.append(char)
                
                # Join and display
                display_str = ''.join(display)
                
                # Status message with animated dots
                status_text = f"{status_messages[status_index]}{dot_states[dots_index]}"
                
                sys.stdout.write(f"{LEFT_BRACKET}{display_str}{RIGHT_BRACKET} {status_text}\033[K")
                
                # Reset cursor position to beginning
                sys.stdout.write('\033[2A\r')
                sys.stdout.flush()
                time.sleep(0.05)  # Smooth animation
                
        finally:
            # Clean up
            sys.stdout.write('\r')
            for _ in range(3):
                sys.stdout.write('\033[K')
                sys.stdout.write('\n')
            sys.stdout.write('\033[3A')
            sys.stdout.write('\033[?25h')
            sys.stdout.flush()

# Utility function for common case - returns a controller with started animation
def start_animation(steps=None, title="AI Research in Progress", animation_type="matrix"):
    """Start an animation with optional custom steps and title
    
    Args:
        steps (list): List of analysis steps to display
        title (str): Title to display at the top of the animation
        animation_type (str): Type of animation to display ("matrix", "sift", "rocket", "elegant")
        
    Returns:
        AnimationController: The started animation controller
    """
    controller = AnimationController(steps, title, animation_type)
    return controller.start() 

# Example usage - uncomment to run
if __name__ == "__main__":
    import time
    
    # Matrix Animation
    print("Running matrix animation for 5 seconds...")
    animation = start_animation(title="Matrix Analysis Demo", animation_type="matrix")
    time.sleep(5)
    animation.stop()
    print("Matrix animation stopped")
    
    # Sift Animation
    print("Running data sift animation for 5 seconds...")
    animation = start_animation(title="Data Sift Search Demo", animation_type="sift")
    time.sleep(5)
    animation.stop()
    print("Data sift animation stopped")
    
    # Rocket Animation
    print("Running rocket animation for 5 seconds...")
    animation = start_animation(title="Fast Processing Demo", animation_type="rocket")
    time.sleep(5)
    animation.stop()
    print("Rocket animation stopped")
    
    # Elegant Animation
    print("Running elegant animation for 5 seconds...")
    animation = start_animation(title="Processing Your Request", animation_type="elegant")
    time.sleep(5)
    animation.stop()
    print("Elegant animation stopped") 