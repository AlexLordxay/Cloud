# scale_kyiv: the captions of "scale" shifted by the 7-second opening over Kyiv, the hook over Maidan, and the credit
# for the satellite pictures while they are on screen.
import os, importlib.util
_spec = importlib.util.spec_from_file_location('base', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scale', 'captions.py'))
base = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(base)
SHIFT = 7.0
DURATION = base.DURATION + SHIFT
CAPTIONS = [(-1.0, 6.0, 'hook', 'Ти навіть\nне уявляєш,\nде ти зараз')] + \
           [(a + SHIFT, b + SHIFT, k, t) for a, b, k, t in base.CAPTIONS if k != 'hook']
CUTS = []
FADE_IN = 0
HOOK_SIZE = base.HOOK_SIZE
END_CARD = base.END_CARD + SHIFT
END_TITLE = base.END_TITLE
CREDITS = [(0.0, 6.0, 'Супутникові знімки: EOxCloudless 2017, EOX IT Services GmbH (Copernicus Sentinel)')] + \
          [(a + SHIFT, b + SHIFT, t) for a, b, t in base.CREDITS]
