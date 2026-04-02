const item = (name, image, step = 1) => ({
  name,
  image: `/items/${image}`,
  step,
});

export const ITEM_CATALOG = {
  standard: [
    item("Battery", "battery.png"),
    item("Board Screw", "board_screw.png", 4),
    item("Damper", "bumper.png"),
    item("C-CW Prop", "c_cw_prop.png"),
    item("Camera Board", "camera_board.png"),
    item("Camera Housing", "camera_housing.png"),
    item("Camera Screw", "camera_screw.png", 2),
    item("Control Board", "control_board.png"),
    item("CW Prop", "cw_prop.png"),
    item("Drone Frame", "frame.png"),
    item("Motor Jig", "motor_jig.png"),
    item("Motor Screw", "motor_screw.png", 3),
    item("Motor", "motor.png"),
  ],
  simplified: [
    item("Battery", "battery.png"),
    item("Board Screw", "board_screw.png", 4),
    item("Damper", "bumper.png"),
    item("C-CW Prop", "c_cw_prop.png"),
    item("Camera Board", "camera_board.png"),
    item("Camera Housing", "camera_housing.png"),
    item("Camera Screw", "camera_screw.png", 2),
    item("Control Board", "control_board.png"),
    item("CW Prop", "cw_prop.png"),
    item("Preassembled Frame", "frame.png"),
  ],
};
