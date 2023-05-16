from collections import namedtuple
from typing import Any

class BotProcedure:

    Step = namedtuple('BotProcedureStep', ['stepId', 'target', 'text', 'prereqs', 'substeps'])
    Prereq = namedtuple('BotProcedurePrereq', ['target', 'operation', 'value', 'unit', 'text'])

    def __init__(self):
        self.restart()
        self.steps: list[BotProcedure.Step] = []

    def restart(self):
        self.cur_step = -1
        self.cur_substep = -2

    def advance(self):
        # check if the procedure has finished
        if self.cur_step < len(self.steps):
            if self.cur_step == -1:
                self.cur_step += 1
            # check if the current step has any more substeps
            if self.cur_substep + 1 < len(self.steps[self.cur_step].substeps):
                self.cur_substep += 1
            else:
                self.cur_step += 1
                self.cur_substep = -1
                if self.cur_step < len(self.steps) and self.cur_substep + 1 < len(self.steps[self.cur_step].substeps):
                    self.cur_substep += 1
            return True
        else:
            return False

    def get_current_step_number(self):
        return self.cur_step, self.cur_substep

    def get_next_step_number(self):
        self.advance()
        return self.get_current_step_number()
    
    def get_step(self, step_number, substep_number) -> Step:
        if step_number == -1 or step_number >= len(self.steps):
            return None
        if substep_number == -1:
            return self.steps[step_number]
        return self.steps[step_number].substeps[substep_number]

    def get_current_step(self):
        step, substep = self.get_current_step_number()
        return self.get_step(step, substep)

    def get_next_step(self):
        step, substep = self.get_next_step_number()
        return self.get_step(step, substep)

    def is_finished(self):
        return self.cur_step == -1 and self.cur_substep == -1

    def todict(self):
        out = [todict(step) for step in self.steps]
        return out

def todict(step: BotProcedure.Step) -> dict[str, Any]:
    d = step._asdict()
    d['prereqs'] = [prereq._asdict() for prereq in step.prereqs]
    d['substeps'] = [todict(substep) for substep in step.substeps]
    return d