# Total solar eclipse, 2 August 2027. Times in seconds of the 72 s video.
DURATION = 72.0
CAPTIONS = [
    (0.6, 7.6, 'hook', '2 серпня 2027:\nдень стане\nніччю'),
    (8.6, 15.4, 'cap', 'Сонце, Місяць і Земля\nвишикуються в одну лінію'),
    (16.8, 23.0, 'cap', 'Тінь Місяця завширшки ~250 км\nпробіжить через пів планети'),
    (23.4, 32.4, 'cap', 'Іспанія, Марокко, Алжир,\nТуніс, Лівія…'),
    (33.6, 40.4, 'cap', 'Найдовше — над Луксором у Єгипті:\n6 хвилин 23 секунди темряви'),
    (41.8, 48.4, 'cap', 'Посеред дня стемніє,\nзасяють зорі й сонячна корона'),
    (49.6, 55.6, 'cap', 'Далі — Аравія, Ємен, Сомалі.\nТінь мчить швидше за літак'),
    (56.8, 63.6, 'cap', 'А в Україні Місяць закриє\nвід третини до половини Сонця'),
    (64.0, 66.8, 'cap', 'Дивись лише крізь\nспеціальні окуляри!'),
]
CUTS = [8.0, 41.0, 49.0, 56.0]   # 16 s: no cut, the camera flies from the line-up down to the shadow
END_CARD = 67.2
END_TITLE = 'Подивись затемнення\nсам'
# A clock (Kyiv time) over the shots where the shadow runs: windows on the video, the time comes from scene.json "clock".
CLOCK_SHOW = [(16.4, 40.6), (49.4, 63.8)]
CLOCK_UTC_OFFSET = 3
CLOCK_LABEL = 'за Києвом'
