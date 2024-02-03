from collections import namedtuple

from .BotProcedure import BotProcedure

EgressStep = BotProcedure.Step
EgressPrereq = BotProcedure.Prereq


class EgressProcedure(BotProcedure):

    def __init__(self):
        super().__init__()
        self.steps = [
            EgressStep(
                stepId="0.0",
                target="all",
                text="Ensure that all switches are set to off",
                prereqs=[],
                substeps=[],
            ),
            EgressStep(
                stepId="1.0",
                target="",
                text="Power on EMU-1",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="1.1",
                        target="emu1_pwr_switch",
                        text="Switch EMU-1 Power to ON",
                        prereqs=[],
                        substeps=[],
                    )
                ],
            ),
            EgressStep(
                stepId="2.0",
                target="",
                text="Prepare UIA",
                prereqs=[
                    EgressPrereq(
                        target="emu1_is_booted",
                        operation="",
                        value="True",
                        unit="",
                        text="SUIT is booted",
                    )
                ],
                substeps=[
                    EgressStep(
                        stepId="2.1",
                        target="o2_vent_switch",
                        text="Switch O2 Vent to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="2.2",
                        target="o2_vent_switch",
                        text="Switch O2 Vent to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_supply_pressure",
                                operation="lt",
                                value="23",
                                unit="psi",
                                text="UIA Supply Pressure < 23 psi",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="3.0",
                target="",
                text="Purge N2",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="3.1",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="3.2",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_supply_pressure",
                                operation="gt",
                                value="3000",
                                unit="psi",
                                text="UIA Supply Pressure > 3000",
                            )
                        ],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="3.3",
                        target="o2_vent_switch",
                        text="Switch O2 Vent to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="3.4",
                        target="o2_vent_switch",
                        text="Switch O2 Supply to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_supply_pressure",
                                operation="lt",
                                value="23",
                                unit="psi",
                                text="UIA Supply Pressure < 23",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="4.0",
                target="",
                text="Initial O2 Pressurization",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="4.1",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="4.2",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_supply_pressure",
                                operation="gt",
                                value="1500",
                                unit="psi",
                                text="UIA Supply Pressure > 1500",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="5.0",
                target="",
                text="Dump EMU Waste Water",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="5.1",
                        target="ev1_water_waste_switch",
                        text="Switch EV-1 Waste to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="5.2",
                        target="ev1_water_waste_switch",
                        text="Switch EV-1 Waste to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_water_level",
                                operation="lt",
                                value="5",
                                unit="percentage",
                                text="EV-1 Water Level < 5%",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="6.0",
                target="",
                text="Refill EMU Waste Water",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="6.1",
                        target="ev1_supply_switch",
                        text="Switch EV-1 Supply to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="6.2",
                        target="ev1_supply_switch",
                        text="Switch EV-1 Supply to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_water_level",
                                operation="gt",
                                value="95",
                                unit="percentage",
                                text="EV-1 Water Level > 95%",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="7.0",
                target="",
                text="Initial Airlock Depressurization",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="7.1",
                        target="depress_pump_switch",
                        text="Switch Depress Pump to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="7.2",
                        target="depress_pump_switch",
                        text="Switch Depress Pump to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="airlock_pressure",
                                operation="lt",
                                value="10.2",
                                unit="psi",
                                text="Airlock Pressure < 10.2",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="8.0",
                target="",
                text="Complete O2 Pressurization",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="8.1",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="8.2",
                        target="emu1_o2_supply_switch",
                        text="Switch O2 Supply to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="uia_supply_pressure",
                                operation="gt",
                                value="3000",
                                unit="psi",
                                text="UIA Supply Pressure > 3000",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
            EgressStep(
                stepId="9.0",
                target="",
                text="Complete Airlock Depressurization",
                prereqs=[],
                substeps=[
                    EgressStep(
                        stepId="9.1",
                        target="depress_pump_switch",
                        text="Switch Depress Pump to OPEN",
                        prereqs=[],
                        substeps=[],
                    ),
                    EgressStep(
                        stepId="9.2",
                        target="depress_pump_switch",
                        text="Switch Depress Pump to CLOSE",
                        prereqs=[
                            EgressPrereq(
                                target="airlock_pressure",
                                operation="lt",
                                value="0.1",
                                unit="psi",
                                text="Airlock Pressure < 0.1",
                            )
                        ],
                        substeps=[],
                    ),
                ],
            ),
        ]


if __name__ == "__main__":
    import json

    egress = EgressProcedure()
    print(json.dumps(egress.todict(), indent=2))

    print("Testing...")
    while egress.advance():
        step = egress.get_current_step()
        if step:
            print(step.stepId, step.text)
