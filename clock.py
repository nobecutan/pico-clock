from clockdata import ClockData
from statemachine import Clock
from rotary_irq_rp2 import RotaryIRQ
from color_setup import ssd

import states
import states_edit

r = RotaryIRQ(pin_num_clk=22,
              pin_num_dt=26,
              pin_num_sw=27)

cd = ClockData()
sm = Clock(ssd, cd)

sm.register_state(states.Init(ssd, cd))
sm.register_state(states.Normal(ssd, cd))

sm.register_state(states_edit.SetHour10(ssd, cd))
sm.register_state(states_edit.SetHour1(ssd, cd))
sm.register_state(states_edit.SetMinute10(ssd, cd))
sm.register_state(states_edit.SetMinute1(ssd, cd))
sm.register_state(states_edit.SetYear(ssd, cd))
sm.register_state(states_edit.SetMonth(ssd, cd))
sm.register_state(states_edit.SetDay(ssd, cd))

r.add_listener(sm.processEvent)

sm.init()
