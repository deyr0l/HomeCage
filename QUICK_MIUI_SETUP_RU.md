# HomeCage quick MIUI setup

Сценарий: телефон уже используется, Google account активен, Device Owner включить нельзя без сброса. Это не такой сильный режим, как Device Owner, но он ближе к consumer parental-control приложениям: Device Admin + Accessibility + overlay + Usage Access + MIUI survival settings.

## 1. Установка

1. Установите APK обычным способом.
2. Откройте HomeCage.
3. Зайдите в `Admin` по PIN.
4. Сразу смените PIN с `1234`.

## 2. Включить защитные слои

В `Admin -> Protection without Device Owner` включите по порядку:

1. `Enable Device Admin`.
2. `Open restricted settings` -> три точки -> `Allow restricted settings`, если Android блокирует Accessibility.
3. `Open HomeCage Accessibility` -> включить сервис HomeCage.
4. `Allow display over apps`.
5. `Open Xiaomi other permissions` -> включить `Display pop-up windows`, `Open new windows while running in the background`, `Show on Lock screen`, если такие пункты есть на этой версии MIUI/HyperOS.
6. `Open Usage Access` -> разрешить HomeCage.
7. `Open Xiaomi autostart` -> включить автозапуск HomeCage.
8. `Open battery settings` -> для HomeCage поставить режим без ограничений.
9. `Allow calls`, если нужны быстрые звонки.
10. `Allow flashlight`, если нужна кнопка фонарика внутри HomeCage.

После этого вернитесь в HomeCage и проверьте, что статусы в блоке защиты стали `enabled/allowed`.

## 3. Минимальный allowlist

Не добавляйте в разрешенные приложения:

- браузеры;
- обычный launcher;
- Settings;
- Security / Permissions / Cleaner / App manager;
- Package installer;
- Play Store / GetApps / Xiaomi Market;
- Contacts и Dialer целиком, если достаточно быстрых звонков.

Для звонков лучше используйте `Quick calls`: HomeCage сам откроет звонок и даст короткую transient-сессию только телефонным компонентам.

Для фонарика не открывайте шторку. Используйте карточку `Flashlight` на главном экране HomeCage.

## 4. Дополнительные package names

Добавляйте туда только support packages, которые нужны как фоновые компоненты, например клавиатура или MIUI plugin. Они больше не считаются самостоятельными разрешенными приложениями: HomeCage разрешает их только поверх уже разрешенного foreground-приложения.

Если после добавления пакета ребенок снова выходит в браузер/settings, пакет нужно убрать и снять package/class trail через ADB или серверные логи.

## 5. Быстрый тест после настройки

1. Нажмите Home и Back несколько раз.
2. Потяните шторку, попробуйте попасть в Settings.
3. Откройте быстрый звонок, завершите звонок, проверьте возврат в HomeCage.
4. Включите и выключите фонарик с главного экрана.
5. Попробуйте открыть App info / Uninstall / Accessibility / Device Admin.
6. Перезагрузите телефон и проверьте, что HomeCage стартует сам.

## Важное ограничение

Без Device Owner Android и MIUI все равно оставляют системные маршруты отключения защиты. Этот режим должен уменьшить поверхность атаки, но не является таким же жестким, как provisioned Device Owner.
