"""Curated library of Manim CE animation templates for the Online Compiler."""

TEMPLATES = [
    {
        "id": "hello_world",
        "name": "👋 Hello Manim (Fast)",
        "description": "Snappy text intro and geometric morphing.",
        "scene_name": "HelloManim",
        "code": '''from manim import *

class HelloManim(Scene):
    def construct(self):
        title = Text("Hello, Manim!", font_size=44, color=BLUE)
        circle = Circle(radius=1.4, color=TEAL)
        square = Square(side_length=2.2, color=YELLOW)
        
        self.play(FadeIn(title, shift=UP), run_time=0.8)
        self.wait(0.4)
        self.play(ReplacementTransform(title, circle), run_time=0.8)
        self.play(Transform(circle, square), Rotate(circle, angle=PI / 2), run_time=0.8)
        self.wait(0.5)
'''
    },
    {
        "id": "math_graph",
        "name": "📈 Function Graph & Area",
        "description": "Plotting mathematical curves, Riemann rectangles, and labels.",
        "scene_name": "FunctionPlotScene",
        "code": '''from manim import *
import numpy as np

class FunctionPlotScene(Scene):
    def construct(self):
        ax = Axes(
            x_range=[0, 6, 1],
            y_range=[-1.5, 1.5, 0.5],
            axis_config={"color": BLUE_C},
            x_axis_config={"numbers_to_include": np.arange(0, 6, 1)},
            tips=False
        )
        
        labels = ax.get_axis_labels(x_label="x", y_label="f(x)")
        
        # Define functions
        sin_graph = ax.plot(lambda x: np.sin(x), color=YELLOW)
        sin_label = ax.get_graph_label(sin_graph, label="\\\\sin(x)", x_val=3.5, direction=UP)
        
        # Riemann rectangles
        rects = ax.get_riemann_rectangles(sin_graph, x_range=[0, PI], dx=0.2, stroke_color=WHITE)
        
        self.play(Create(ax), Write(labels))
        self.play(Create(sin_graph), run_time=2)
        self.play(FadeIn(sin_label))
        self.wait(0.5)
        self.play(Create(rects), run_time=2)
        self.wait(1.5)
'''
    },
    {
        "id": "latex_formula",
        "name": "🧮 LaTeX Math Transformation",
        "description": "Euler's identity and algebraic transformations.",
        "scene_name": "EulerIdentity",
        "code": '''from manim import *

class EulerIdentity(Scene):
    def construct(self):
        formula1 = MathTex("e^{i\\\\theta} = \\\\cos(\\\\theta) + i\\\\sin(\\\\theta)")
        formula2 = MathTex("e^{i\\\\pi} = \\\\cos(\\\\pi) + i\\\\sin(\\\\pi)")
        formula3 = MathTex("e^{i\\\\pi} = -1 + 0")
        formula4 = MathTex("e^{i\\\\pi} + 1 = 0")
        
        # Color specific parts
        formula4.set_color_by_tex("e", YELLOW)
        formula4.set_color_by_tex("i", RED)
        formula4.set_color_by_tex("\\\\pi", GREEN)
        formula4.set_color_by_tex("1", BLUE)
        formula4.set_color_by_tex("0", PURPLE)
        
        title = Text("Euler\'s Identity", font_size=36, color=GOLD).to_edge(UP)
        
        self.play(Write(title))
        self.play(Write(formula1))
        self.wait(1)
        self.play(Transform(formula1, formula2))
        self.wait(1)
        self.play(Transform(formula1, formula3))
        self.wait(1)
        self.play(Transform(formula1, formula4))
        self.wait(2)
'''
    },
    {
        "id": "threed_surface",
        "name": "🌐 3D Surface & Camera Orbit",
        "description": "3D coordinate system, torus/surface with camera rotation.",
        "scene_name": "ThreeDOrbitScene",
        "code": '''from manim import *
import numpy as np

class ThreeDOrbitScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        surface = Surface(
            lambda u, v: np.array([
                u,
                v,
                0.4 * np.sin(u) * np.cos(v)
            ]),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            should_make_jagged=False
        )
        surface.set_style(fill_opacity=0.8, fill_color=BLUE_D, stroke_color=LIGHT_GREY)
        
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        self.play(Create(axes), Create(surface), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.4)
        self.wait(3)
        self.stop_ambient_camera_rotation()
        self.wait(0.5)
'''
    },
    {
        "id": "neural_network",
        "name": "🧠 Neural Network Architecture",
        "description": "Animated visual representation of neural network layers and activations.",
        "scene_name": "NeuralNetScene",
        "code": '''from manim import *

class NeuralNetScene(Scene):
    def construct(self):
        layer_sizes = [3, 4, 2]
        layer_colors = [BLUE, GREEN, ORANGE]
        layers = []
        
        # Create neurons
        for i, size in enumerate(layer_sizes):
            layer = VGroup()
            for j in range(size):
                neuron = Circle(radius=0.25, color=layer_colors[i], fill_opacity=0.7)
                neuron.move_to(np.array([i * 2.5 - 2.5, j * 0.9 - (size - 1) * 0.45, 0]))
                layer.add(neuron)
            layers.append(layer)
        
        # Create synapses
        connections = VGroup()
        for i in range(len(layers) - 1):
            for n1 in layers[i]:
                for n2 in layers[i+1]:
                    line = Line(n1.get_center(), n2.get_center(), stroke_width=1.5, color=GRAY_B)
                    connections.add(line)
        
        title = Text("Deep Neural Network", font_size=32).to_edge(UP)
        self.play(Write(title))
        self.play(FadeIn(connections, lag_ratio=0.01), run_time=1.5)
        for layer in layers:
            self.play(Create(layer), run_time=0.6)
            
        # Pulse signal across network
        pulses = []
        for n1 in layers[0]:
            for n2 in layers[1]:
                dot = Dot(n1.get_center(), color=YELLOW, radius=0.08)
                pulses.append(dot.animate.move_to(n2.get_center()))
        self.play(*pulses, run_time=1.2)
        self.wait(1)
'''
    }
]

def get_templates():
    return TEMPLATES

def get_template_by_id(template_id: str):
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
