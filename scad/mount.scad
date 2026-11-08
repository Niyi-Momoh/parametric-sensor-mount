// Parametric pan mount for an HC-SR04 ultrasonic sensor on an SG90 micro servo.
// Dimensions are typical published values. Measure your own parts before printing.

part = "assembly"; // bracket, cradle, servo, sensor, beam or assembly
angle = 30;        // pan angle used by the assembly preview

/* [Printing] */
clearance = 0.3;
wall = 3;
min_wall = 1.6;
pilot_diameter = 1.8;
pilot_depth = 8;
$fn = 72;

/* [SG90 servo] */
servo_length = 22.5;
servo_width = 11.8;
servo_height = 22.7;
tab_span = 32.2;
tab_thickness = 2.5;
tab_underside = 15.9;
tab_hole_spacing = 27.5;
shaft_offset = 5.35;
gear_tower_height = 3;
shaft_stub = 1;
shaft_diameter = 5;

/* [Servo horn] */
horn_thickness = 1.5;
horn_hub_diameter = 7.8;
horn_arm_length = 17;
horn_tip_width = 4;
horn_root_width = 6;
horn_recess = 1.6;
horn_screw_diameter = 2.4;

/* [HC-SR04 sensor] */
board_width = 45;
board_height = 20;
board_thickness = 1.6;
can_diameter = 16;
can_spacing = 26;
can_length = 12;
board_margin = 1;
board_fit = 0.25;
beam_half_angle = 15;
beam_length = 120;

/* [Bracket] */
floor_thickness = 3;
under_servo_gap = 1;
flange_length = 60;
flange_width = 34;
flange_thickness = 3;
flange_corner = 3;
chassis_hole_x = 25;
chassis_hole_y = 12.5;
chassis_hole_diameter = 3.4;
cable_window_width = 8;

/* [Cradle] */
hub_width = 28;
hub_back = 11;
hub_thickness = 5;
frame_offset = 18.5;
rail_wall = 2;
front_lip = 1.5;
rear_lip = 1.5;
groove_depth = 2;
strip_height = 3;
frame_top_margin = 1;
gusset_width = 3;
gusset_height = 14;
gusset_length = 11;

eps = 0.01;

assert(wall >= min_wall, "wall is too thin to print reliably");
assert(clearance >= 0 && clearance <= 1, "clearance must be between 0 and 1 mm");
assert(board_margin > 0 && board_margin < board_width / 2, "invalid board margin");
assert((board_width / 2 - board_margin) * 2 > can_spacing + can_diameter,
       "the sensor cans do not fit through the front opening");
assert(groove_depth > board_thickness, "the groove is too shallow for the board");
assert(horn_recess > 0 && horn_recess < hub_thickness - 1, "invalid horn recess");
assert(frame_offset > horn_arm_length, "the frame would overlap the horn arm");
assert(floor_thickness + under_servo_gap + tab_underside - pilot_depth - 1
       > floor_thickness + under_servo_gap, "the cable window would reach the pilot hole");

body_center_x = -shaft_offset;
servo_bottom_z = floor_thickness + under_servo_gap;
tab_z = servo_bottom_z + tab_underside;
block_length = tab_span + 2 * wall;
block_width = servo_width + 2 * clearance + 2 * wall;
shaft_top_z = servo_bottom_z + servo_height + gear_tower_height + shaft_stub;
cradle_z = shaft_top_z + horn_thickness - horn_recess;
groove_half = board_width / 2 + board_fit;
frame_half = groove_half + rail_wall;
frame_depth = rear_lip + groove_depth + front_lip;
front_opening_half = board_width / 2 - board_margin;
board_bottom_z = hub_thickness + strip_height;
frame_top_z = board_bottom_z + board_height + frame_top_margin;
board_center_y = frame_offset + rear_lip + groove_depth / 2;
board_front_y = board_center_y + board_thickness / 2;
can_center_z = board_bottom_z + board_height / 2;

echo(str("INFO cradle_z=", cradle_z));
echo(str("INFO bracket_top_z=", tab_z));
echo(str("INFO radial_reach=", sqrt(pow(frame_half, 2) + pow(frame_offset + frame_depth, 2))));

module flange() {
    translate([body_center_x, 0, 0])
        linear_extrude(flange_thickness)
            offset(r = flange_corner)
                square([flange_length - 2 * flange_corner, flange_width - 2 * flange_corner],
                       center = true);
}

module bracket() {
    difference() {
        union() {
            flange();
            translate([body_center_x - block_length / 2, -block_width / 2, 0])
                cube([block_length, block_width, tab_z]);
        }
        // Servo pocket.
        translate([body_center_x - servo_length / 2 - clearance,
                   -servo_width / 2 - clearance, floor_thickness])
            cube([servo_length + 2 * clearance, servo_width + 2 * clearance, tab_z]);
        // Pilot holes for the servo tab screws.
        for (side = [-1, 1])
            translate([body_center_x + side * tab_hole_spacing / 2, 0, tab_z - pilot_depth])
                cylinder(d = pilot_diameter, h = pilot_depth + eps);
        // Cable window, below the pilot hole.
        translate([body_center_x - block_length / 2 - eps, -cable_window_width / 2, servo_bottom_z])
            cube([(block_length - servo_length) / 2 + 2 * eps, cable_window_width,
                  tab_z - pilot_depth - 1 - servo_bottom_z]);
        // Chassis holes.
        for (x = [-1, 1], y = [-1, 1])
            translate([body_center_x + x * chassis_hole_x, y * chassis_hole_y, -eps])
                cylinder(d = chassis_hole_diameter, h = flange_thickness + 2 * eps);
    }
}

module horn_recess_shape() {
    translate([0, 0, -eps])
        linear_extrude(horn_recess + eps) {
            circle(d = horn_hub_diameter);
            hull() {
                circle(d = horn_root_width);
                translate([0, horn_arm_length - horn_tip_width / 2])
                    circle(d = horn_tip_width);
            }
        }
}

module frame() {
    difference() {
        translate([-frame_half, frame_offset, hub_thickness])
            cube([2 * frame_half, frame_depth, frame_top_z - hub_thickness]);
        // Vertical groove. The board slides in from the top.
        translate([-groove_half, frame_offset + rear_lip, board_bottom_z])
            cube([2 * groove_half, groove_depth, board_height + frame_top_margin + eps]);
        // Front opening for the transducer cans.
        translate([-front_opening_half, frame_offset + frame_depth - front_lip - eps, board_bottom_z])
            cube([2 * front_opening_half, front_lip + 2 * eps,
                  board_height + frame_top_margin + eps]);
        // Rear opening for components and the connector.
        translate([-front_opening_half, frame_offset - eps, board_bottom_z])
            cube([2 * front_opening_half, rear_lip + 2 * eps,
                  board_height + frame_top_margin + eps]);
    }
}

module gussets() {
    for (side = [-1, 1])
        hull() {
            translate([side * (frame_half - gusset_width / 2) - gusset_width / 2,
                       frame_offset - gusset_length, hub_thickness - eps])
                cube([gusset_width, gusset_length, eps]);
            translate([side * (frame_half - gusset_width / 2) - gusset_width / 2,
                       frame_offset - eps, hub_thickness - eps])
                cube([gusset_width, eps, gusset_height]);
        }
}

module cradle() {
    difference() {
        union() {
            translate([-hub_width / 2, -hub_back, 0])
                cube([hub_width, hub_back + frame_offset + frame_depth, hub_thickness]);
            translate([-frame_half, frame_offset, 0])
                cube([2 * frame_half, frame_depth, hub_thickness]);
            frame();
            gussets();
        }
        horn_recess_shape();
        translate([0, 0, -eps])
            cylinder(d = horn_screw_diameter, h = hub_thickness + 2 * eps);
    }
}

module servo() {
    translate([body_center_x - servo_length / 2, -servo_width / 2, servo_bottom_z])
        cube([servo_length, servo_width, servo_height]);
    translate([body_center_x - tab_span / 2, -servo_width / 2, tab_z])
        cube([tab_span, servo_width, tab_thickness]);
    translate([0, 0, servo_bottom_z + servo_height - eps])
        cylinder(d = servo_width, h = gear_tower_height);
    translate([0, 0, servo_bottom_z + servo_height + gear_tower_height - eps])
        cylinder(d = shaft_diameter, h = shaft_stub + eps);
}

module sensor() {
    translate([-board_width / 2, board_center_y - board_thickness / 2, board_bottom_z])
        cube([board_width, board_thickness, board_height]);
    for (side = [-1, 1])
        translate([side * can_spacing / 2, board_front_y - eps, can_center_z])
            rotate([-90, 0, 0])
                cylinder(d = can_diameter, h = can_length + eps);
    // Rear components.
    translate([-15, board_center_y - board_thickness / 2 - 2, board_bottom_z + 5])
        cube([30, 2 + eps, 12]);
    // Connector pins.
    translate([-6, board_center_y - board_thickness / 2 - 7, board_bottom_z])
        cube([12, 7 + eps, 3]);
}

module beam() {
    start_y = board_front_y + can_length;
    start_radius = can_diameter / 2;
    for (side = [-1, 1])
        translate([side * can_spacing / 2, start_y, can_center_z])
            rotate([-90, 0, 0])
                cylinder(r1 = start_radius,
                         r2 = start_radius + beam_length * tan(beam_half_angle),
                         h = beam_length);
}

module assembly() {
    color("#d1d5db") bracket();
    color("#1f2937") servo();
    rotate([0, 0, angle])
        translate([0, 0, cradle_z]) {
            color("#2563eb") cradle();
            color("#16a34a") sensor();
        }
}

if (part == "bracket") bracket();
else if (part == "cradle") cradle();
else if (part == "servo") servo();
else if (part == "sensor") sensor();
else if (part == "beam") beam();
else assembly();
