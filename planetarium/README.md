# Планетарій

Інтерактивна 3D-модель Сонячної системи на Three.js.

## Запуск

Текстури завантажуються як окремі файли, тому сторінку треба відкривати через вебсервер, а не подвійним кліком:

```bash
cd planetarium
python3 -m http.server 8000
# відкрийте http://localhost:8000
```

## Джерела текстур

- Сонце, Венера (атмосфера), Земля (день), Місяць, Марс, Юпітер, Сатурн і його кільця, Уран, Нептун — [Solar System Scope](https://www.solarsystemscope.com/textures/), ліцензія [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), на основі даних NASA.
- Меркурій — NASA / JHUAPL / Carnegie Institution, місія MESSENGER.
- Нічні вогні Землі, маска океанів і хмари — [приклади three.js](https://github.com/mrdoob/three.js/tree/dev/examples/textures/planets).

Текстури зменшено й перестиснено для вебу.
