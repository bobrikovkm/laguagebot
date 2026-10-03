import asyncio
import logging
import os
import random
import sqlite3
import sys
import base64
from datetime import datetime

# Принудительно устанавливаем UTF-8 для терминала macOS/Linux
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка обязательных переменных окружения перед запуском
missing_env = []
if not TOKEN:
    missing_env.append("BOT_TOKEN")
if not OPENAI_API_KEY:
    missing_env.append("OPENAI_API_KEY")

if missing_env:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не заданы переменные окружения: {', '.join(missing_env)}!")
    print("👉 Добавьте их в локальный файл .env или в настройки вашего хостинга (Render).")
    sys.exit(1)

# Инициализация клиента OpenAI и бота
client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Список поддерживаемых языков с флажками стран
LANGUAGES = {
    "uk": "🇺🇦 Українська",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "es": "🇪🇸 Español",
    "it": "🇮🇹 Italiano",
    "ar": "🇸🇦 العربية"
}

# Доступные уровни языка
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Сценарии общения (Ролевые игры)
SCENARIOS = {
    "tutor": {
        "ru": "👨‍‍🏫 Репетитор", "uk": "👨‍🏫 Репетитор", "en": "👨‍🏫 Tutor", "fr": "👨‍🏫 Tuteur",
        "de": "👨‍🏫 Tutor", "es": "👨‍🏫 Tutor", "it": "👨‍🏫 Tutor", "ar": "👨‍🏫 معلم"
    },
    "translator": {
        "ru": "💬 Режим переводчика", "uk": "💬 Режим перекладача", "en": "💬 Translator mode", "fr": "💬 Mode traducteur",
        "de": "💬 Übersetzungsmodus", "es": "💬 Modo traductor", "it": "💬 Modalità traduttore", "ar": "💬 وضع المترجم"
    },
    "interview": {
        "ru": "💼 Собеседование", "uk": "💼 Співбесіда", "en": "💼 Interview", "fr": "💼 Entretien",
        "de": "💼 Vorstellungsgespräch", "es": "💼 Entrevista", "it": "💼 Colloquio", "ar": "💼 مقابلة عمل"
    },
    "airport": {
        "ru": "✈️ В аэропорту", "uk": "✈️ В аеропорту", "en": "✈️ At the airport", "fr": "✈️ À l'aéroport",
        "de": "✈️ Am Flughafen", "es": "✈️ En el aeropuerto", "it": "✈️ All'aeroporto", "ar": "✈️ في المطار"
    },
    "shop": {
        "ru": "🛍 В магазине", "uk": "🛍️ В магазині", "en": "🛍️ At the shop", "fr": "🛍️ Au magasin",
        "de": "🛍️ Im Geschäft", "es": "🛍️ En la tienda", "it": "🛍️ Al negozio", "ar": "🛍️ في المتجر"
    },
    "hospital": {
        "ru": "🏥 В больнице", "uk": "🏥 У лікарні", "en": "🏥 At the hospital", "fr": "🏥 À l'hôpital",
        "de": "🏥 Im Krankenhaus", "es": "🏥 En el hospital", "it": "🏥 All'ospedale", "ar": "🏥 في المستشفى"
    },
    "restaurant": {
        "ru": "🍽️ В ресторане", "uk": "🍽️ У ресторані", "en": "🍽️ At the restaurant", "fr": "🍽️ Au restaurant",
        "de": "🍽️ Im Restaurant", "es": "🍽️ En el restaurante", "it": "🍽️ Al ristorante", "ar": "🍽️ في المطعم"
    },
    "travel": {
        "ru": "🧳 В путешествии", "uk": "🧳 У подорожі", "en": "🧳 Traveling", "fr": "🧳 En voyage",
        "de": "🧳 Auf Reisen", "es": "🧳 De viaje", "it": "🧳 In viaggio", "ar": "🧳 في السفر"
    }
}

# Полная локализация текстов и интерфейса
TRANSLATIONS = {
    "ru": {
        "welcome": "👋 Привет! Давай настроим твой профиль. Выбери свой родной язык:",
        "target": "Отлично! Теперь выбери язык, который хочешь изучать:",
        "scenario": "Превосходно! Выбери сценарий общения:",
        "done": "✅ Настройка завершена!\n\n💬 Теперь ты можешь отправлять **текстовые** сообщения, 🎙 записывать **голосовые** или 📷 отправлять **фотографии с текстом** для перевода.\n\n👉 *Нажми кнопку **Menu** слева от чата, чтобы посмотреть команды.*",
        "profile_title": "ПАСПОРТ ИЗУЧЕНИЯ ЯЗЫКА",
        "native_lang": "Родной язык",
        "target_lang": "Изучаемый язык",
        "scenario_label": "Сценарий",
        "streak_label": "Стрик занятий",
        "level_label": "Уровень",
        "msgs_label": "Отправлено сообщений",
        "error": "Извини, произошла ошибка при связи с ИИ.",
        "audio_error": "Не удалось сгенерировать аудио.",
        "grammar_title": "💡 Грамматический разбор:",
        "saved": "✅ Фраза успешно сохранена в твой словарь!",
        "profile_not_found": "Профиль не найден. Напиши /start",
        "vocabulary_title": "Твой словарь сохраненных фраз:",
        "empty_vocabulary": "📭 Твой словарь пока пуст. Нажимай кнопку «💾 Сохранить фразу» под сообщениями бота, чтобы добавлять их сюда!",
        "deleted": "✅ Фраза удалена из словаря!",
        "settings_title": "⚙️ **Настройки профиля:**\nВыбери, что именно хочешь изменить:",
        "btn_native": "🌍 Родной язык",
        "btn_target": "🎯 Изучаемый язык",
        "btn_scenario": "🎭 Сценарий",
        "level_title": "📊 Твой текущий уровень: **{level}**.\nВыбери новый уровень владения языком:",
        "level_updated": "✅ Уровень успешно изменен на **{level}**!",
        "empty_vocab_quiz": "📭 Твой словарь пуст! Сначала сохрани хотя бы одну фразу через кнопку «💾 Сохранить фразу» под ответами бота, чтобы проходить квизы.",
        "quiz_title": "🧠 **Интерактивный квиз по твоему словарю:**",
        "quiz_correct": "✅ **Верно!** Отличная работа 🎉",
        "quiz_incorrect": "❌ **Неверно.** Правильный вариант: **{correct}**",
        "challenge_title": "🎯 **Твой ежедневный вызов (Challenge):**",
        "stats_title": "📈 **Расширенная статистика:**",
        "vocab_count": "Сохранено фраз",
        "settings_updated": "✅ Настройки успешно обновлены!",
        "photo_processing": "🔍 <i>Распознаю текст на фото и перевожу...</i>",
        "btn_repeat_audio": "🔊 Прослушать еще раз",
        "btn_explain_grammar": "💡 Объяснить правило",
        "btn_save_phrase": "💾 Сохранить фразу",
        "reminder_set": "✅ Время ежедневного напоминания успешно установлено на **{time}**!",
        "reminder_prompt": "⏰ **Время для 15-минутного урока!** Пора позаниматься языком с твоим ИИ-репетитором.",
        "daily_phrase_title": "🌟 **Фраза дня (уровень {level}):**",
        "challenge_100_title": "🏆 **Челлендж 100 дней обучения:**",
        "recognized": "🗣 <i>Распознано:</i> "
    },
    "uk": {
        "welcome": "👋 Привіт! Давай налаштуємо твій профіль. Вибери свою рідну мову:",
        "target": "Чудово! Тепер вибери мову, яку хочеш вивчати:",
        "scenario": "Чудово! Вибери сценарій спілкування:",
        "done": "✅ Налаштування завершено!\n\n💬 Тепер ти можеш надсилати **текстові** повідомлення, 🎙 записувати **голосові** або 📷 надсилати **фотографії з текстом** для перекладу.\n\n👉 *Натисни кнопку **Menu** зліва від чату, щоб переглянути команди.*",
        "profile_title": "ПАСПОРТ ВИВЧЕННЯ МОВИ",
        "native_lang": "Рідна мова",
        "target_lang": "Мова, що вивчається",
        "scenario_label": "Сценарій",
        "streak_label": "Стрік занять",
        "level_label": "Рівень",
        "msgs_label": "Надіслано повідомлень",
        "error": "Вибач, сталася помилка під час зв'язку з ШІ.",
        "audio_error": "Не вдалося згенерувати аудіо.",
        "grammar_title": "💡 Граматичний розбір:",
        "saved": "✅ Фразу успішно збережено до твого словника!",
        "profile_not_found": "Профіль не знайдено. Напиши /start",
        "vocabulary_title": "Твій словник збережених фраз:",
        "empty_vocabulary": "📭 Твій словник поки що порожній. Натискай кнопку «💾 Зберегти фразу» під повідомленнями бота, щоб додавати їх сюди!",
        "deleted": "✅ Фразу видалено зі словника!",
        "settings_title": "⚙️ **Налаштування профілю:**\nВибери, що саме хочеш змінити:",
        "btn_native": "🌍 Рідна мова",
        "btn_target": "🎯 Мова, що вивчається",
        "btn_scenario": "🎭 Сценарій",
        "level_title": "📊 Твій поточний рівень: **{level}**.\nВибери новий рівень володіння мовою:",
        "level_updated": "✅ Рівень успішно змінено на **{level}**!",
        "empty_vocab_quiz": "📭 Твій словник порожній! Спочатку збережи хоча б одну фразу через кнопку «💾 Зберегти фразу» під відповідями бота.",
        "quiz_title": "🧠 **Інтерактивний квиз за твоїм словником:**",
        "quiz_correct": "✅ **Правильно!** Чудова робота 🎉",
        "quiz_incorrect": "❌ **Неправильно.** Правильний варіант: **{correct}**",
        "challenge_title": "🎯 **Твій щоденний виклик (Challenge):**",
        "stats_title": "📈 **Розширена статистика:**",
        "vocab_count": "Збережено фраз",
        "settings_updated": "✅ Налаштування успішно оновлено!",
        "photo_processing": "🔍 <i>Розпізнаю текст на фото та перекладаю...</i>",
        "btn_repeat_audio": "🔊 Прослухати ще раз",
        "btn_explain_grammar": "💡 Пояснити правило",
        "btn_save_phrase": "💾 Зберегти фразу",
        "reminder_set": "✅ Час щоденного нагадування успішно встановлено на **{time}**!",
        "reminder_prompt": "⏰ **Час для 15-хвилинного уроку!** Пора зайнятися мовою з твоїм ШІ-репетитором.",
        "daily_phrase_title": "🌟 **Фраза дня (рівень {level}):**",
        "challenge_100_title": "🏆 **Челендж 100 днів навчання:**",
        "recognized": "🗣 <i>Розпізнано:</i> "
    },
    "en": {
        "welcome": "👋 Hello! Let's set up your profile. Choose your native language:",
        "target": "Great! Now choose the language you want to learn:",
        "scenario": "Awesome! Choose a communication scenario:",
        "done": "✅ Setup complete!\n\n💬 You can now send **text** messages, 🎙️ record **voice messages** or 📷 send **photos with text** for translation.\n\n👉 *Tap the **Menu** button next to the chat input to see all commands.*",
        "profile_title": "LANGUAGE PASSPORT",
        "native_lang": "Native language",
        "target_lang": "Target language",
        "scenario_label": "Scenario",
        "streak_label": "Streak",
        "level_label": "Level",
        "msgs_label": "Messages sent",
        "error": "Sorry, an error occurred while connecting to AI.",
        "audio_error": "Failed to generate audio.",
        "grammar_title": "💡 Grammar explanation:",
        "saved": "✅ Phrase successfully saved to your vocabulary!",
        "profile_not_found": "Profile not found. Type /start",
        "vocabulary_title": "Your saved vocabulary:",
        "empty_vocabulary": "📭 Your vocabulary is empty yet. Click '💾 Save phrase' under bot messages to add them here!",
        "deleted": "✅ Phrase deleted from vocabulary!",
        "settings_title": "⚙️ **Profile Settings:**\nChoose what you want to change:",
        "btn_native": "🌍 Native language",
        "btn_target": "🎯 Target language",
        "btn_scenario": "🎭 Scenario",
        "level_title": "📊 Your current level: **{level}**.\nChoose your new language proficiency level:",
        "level_updated": "✅ Level successfully updated to **{level}**!",
        "empty_vocab_quiz": "📭 Your vocabulary is empty! Save at least one phrase using the '💾 Save phrase' button first.",
        "quiz_title": "🧠 **Interactive Vocabulary Quiz:**",
        "quiz_correct": "✅ **Correct!** Great job 🎉",
        "quiz_incorrect": "❌ **Incorrect.** The correct option is: **{correct}**",
        "challenge_title": "🎯 **Your Daily Challenge:**",
        "stats_title": "📈 **Extended Statistics:**",
        "vocab_count": "Saved phrases",
        "settings_updated": "✅ Settings successfully updated!",
        "photo_processing": "🔍 <i>Recognizing text in the photo and translating...</i>",
        "btn_repeat_audio": "🔊 Listen again",
        "btn_explain_grammar": "💡 Explain grammar",
        "btn_save_phrase": "💾 Save phrase",
        "reminder_set": "✅ Daily reminder time successfully set to **{time}**!",
        "reminder_prompt": "⏰ **Time for a 15-minute study break!** Time to practice languages with your AI tutor.",
        "daily_phrase_title": "🌟 **Phrase of the day (level {level}):**",
        "challenge_100_title": "🏆 **100-Day Learning Challenge:**",
        "recognized": "🗣 <i>Recognized:</i> "
    },
    "fr": {
        "welcome": "👋 Bonjour ! Configurons votre profil. Choisissez votre langue maternelle :",
        "target": "Super ! Choisissez maintenant la langue que vous souhaitez apprendre :",
        "scenario": "Parfait ! Choisissez un scénario de communication :",
        "done": "✅ Configuration terminée !\n\n💬 Vous pouvez désormais envoyer des messages **textes**, 🎙️ enregistrer des **messages vocaux** ou 📷 envoyer des **photos avec du texte** pour traduction.\n\n👉 *Appuyez sur le bouton **Menu** à côté du chat pour voir les commandes.*",
        "profile_title": "PASSEPORT LINGUISTIQUE",
        "native_lang": "Langue maternelle",
        "target_lang": "Langue cible",
        "scenario_label": "Scénario",
        "streak_label": "Série",
        "level_label": "Niveau",
        "msgs_label": "Messages envoyés",
        "error": "Erreur de connexion avec l'IA.",
        "audio_error": "Erreur audio.",
        "grammar_title": "💡 Explication grammaticale :",
        "saved": "✅ Phrase enregistrée dans votre vocabulaire !",
        "profile_not_found": "Profil introuvable. Tapez /start",
        "vocabulary_title": "Votre vocabulaire enregistré :",
        "empty_vocabulary": "📭 Votre vocabulaire est vide. Cliquez sur « 💾 Enregistrer la phrase » sous les messages !",
        "deleted": "✅ Phrase supprimée !",
        "settings_title": "⚙️ **Paramètres du profil :**",
        "btn_native": "🌍 Langue maternelle",
        "btn_target": "🎯 Langue cible",
        "btn_scenario": "🎭 Scénario",
        "level_title": "📊 Niveau actuel : **{level}**.\nChoisissez votre nouveau niveau :",
        "level_updated": "✅ Niveau mis à jour à **{level}** !",
        "empty_vocab_quiz": "📭 Vocabulaire vide ! Enregistrez d'abord une phrase.",
        "quiz_title": "🧠 **Quiz interactif :**",
        "quiz_correct": "✅ **Correct !** Bravo 🎉",
        "quiz_incorrect": "❌ **Incorrect.** La bonne option est : **{correct}**",
        "challenge_title": "🎯 **Votre défi quotidien :**",
        "stats_title": "📈 **Statistiques :**",
        "vocab_count": "Phrases enregistrées",
        "settings_updated": "✅ Paramètres mis à jour !",
        "photo_processing": "🔍 <i>Reconnaissance du texte sur la photo...</i>",
        "btn_repeat_audio": "🔊 Réécouter",
        "btn_explain_grammar": "💡 Expliquer la règle",
        "btn_save_phrase": "💾 Enregistrer la phrase",
        "reminder_set": "✅ Rappel quotidien défini à **{time}** !",
        "reminder_prompt": "⏰ **C'est l'heure de la pause d'étude de 15 minutes !** Pratiquez avec votre tuteur IA.",
        "daily_phrase_title": "🌟 **Phrase du jour (niveau {level}) :**",
        "challenge_100_title": "🏆 **Défi 100 jours d'apprentissage :**",
        "recognized": "🗣 <i>Reconnu :</i> "
    },
    "de": {
        "welcome": "👋 Hallo! Lass uns dein Profil einrichten. Wähle deine Muttersprache:",
        "target": "Super! Wähle nun die Sprache, die du lernen möchtest:",
        "scenario": "Perfekt! Wähle ein Kommunikationsszenario:",
        "done": "✅ Einrichtung abgeschlossen!\n\n💬 Du kannst jetzt **Textnachrichten** senden, 🎙 **Sprachnachrichten** aufnehmen oder 📷 **Fotos mit Text** zur Übersetzung senden.\n\n👉 *Tippe auf die Schaltfläche **Menu** links neben dem Chat, um alle Befehle anzuzeigen.*",
        "profile_title": "SPRACHPASS",
        "native_lang": "Muttersprache",
        "target_lang": "Zielsprache",
        "scenario_label": "Szenario",
        "streak_label": "Streak",
        "level_label": "Niveau",
        "msgs_label": "Gesendete Nachrichten",
        "error": "Entschuldigung, bei der Verbindung mit der KI ist ein Fehler aufgetreten.",
        "audio_error": "Audio konnte nicht generiert werden.",
        "grammar_title": "💡 Grammatikerklärung:",
        "saved": "✅ Phrase erfolgreich im Vokabular gespeichert!",
        "profile_not_found": "Profil nicht gefunden. Schreibe /start",
        "vocabulary_title": "Dein gespeichertes Vokabular:",
        "empty_vocabulary": "📭 Dein Vokabular ist noch leer. Klicke auf „💾 Phrase speichern“ unter Bot-Nachrichten, um welche hinzuzufügen!",
        "deleted": "✅ Phrase aus dem Vokabular gelöscht!",
        "settings_title": "⚙️ **Profileinstellungen:**\nWähle aus, was du ändern möchtest:",
        "btn_native": "🌍 Muttersprache",
        "btn_target": "🎯 Zielsprache",
        "btn_scenario": "🎭 Szenario",
        "level_title": "📊 Dein aktuelles Niveau: **{level}**.\nWähle dein neues Sprachniveau:",
        "level_updated": "✅ Niveau erfolgreich auf **{level}** aktualisiert!",
        "empty_vocab_quiz": "📭 Dein Vokabular ist leer! Speichere zuerst mindestens eine Phrase über die Schaltfläche „💾 Phrase speichern“.",
        "quiz_title": "🧠 **Interaktives Vokabelquiz:**",
        "quiz_correct": "✅ **Richtig!** Tolle Arbeit 🎉",
        "quiz_incorrect": "❌ **Falsch.** Die richtige Option ist: **{correct}**",
        "challenge_title": "🎯 **Deine Tägliche Challenge:**",
        "stats_title": "📈 **Erweiterte Statistiken:**",
        "vocab_count": "Gespeicherte Phrasen",
        "settings_updated": "✅ Einstellungen erfolgreich aktualisiert!",
        "photo_processing": "🔍 <i>Erkenne Text auf dem Foto und übersetze...</i>",
        "btn_repeat_audio": "🔊 Noch einmal anhören",
        "btn_explain_grammar": "💡 Regel erklären",
        "btn_save_phrase": "💾 Phrase speichern",
        "reminder_set": "✅ Tägliche Lern-Erinnerung erfolgreich auf **{time}** eingestellt!",
        "reminder_prompt": "⏰ **15-Minuten-Lernpause!** Zeit, deine Sprachkenntnisse mit deinem KI-Tutor zu verbessern.",
        "daily_phrase_title": "🌟 **Phrase des Tages (Niveau {level}):**",
        "challenge_100_title": "🏆 **100-Tage-Lernchallenge:**",
        "recognized": "🗣 <i>Erkannt:</i> "
    },
    "es": {
        "welcome": "👋 ¡Hola! Configuremos tu perfil. Elige tu idioma nativo:",
        "target": "¡Genial! Ahora elige el idioma que quieres aprender:",
        "scenario": "¡Perfecto! Elige un escenario de comunicación:",
        "done": "✅ ¡Configuración completada!\n\n💬 Ahora puedes enviar **mensajes de texto**, 🎙️ grabar **notas de voz** o 📷 enviar **fotos con texto** para traducir.\n\n👉 *Toca el botón **Menu** junto al chat para ver los comandos.*",
        "profile_title": "PASAPORTE DE IDIOMAS",
        "native_lang": "Idioma nativo",
        "target_lang": "Idioma de estudio",
        "scenario_label": "Escenario",
        "streak_label": "Racha",
        "level_label": "Nivel",
        "msgs_label": "Mensajes enviados",
        "error": "Error de conexión con la IA.",
        "audio_error": "Error de audio.",
        "grammar_title": "💡 Explicación gramatical:",
        "saved": "✅ ¡Frase guardada en tu vocabulario!",
        "profile_not_found": "Perfil no encontrado. Escribe /start",
        "vocabulary_title": "Tu vocabulario guardado:",
        "empty_vocabulary": "📭 Tu vocabulario está vacío. ¡Haz clic en '💾 Guardar frase' bajo los mensajes!",
        "deleted": "✅ ¡Frase eliminada!",
        "settings_title": "⚙️ **Ajustes del perfil:**",
        "btn_native": "🌍 Idioma nativo",
        "btn_target": "🎯 Idioma de estudio",
        "btn_scenario": "🎭 Escenario",
        "level_title": "📊 Nivel actual: **{level}**.\nElige tu nuevo nivel:",
        "level_updated": "✅ ¡Nivel actualizado a **{level}**!",
        "empty_vocab_quiz": "📭 ¡Vocabulario vacío! Guarda al menos una frase primero.",
        "quiz_title": "🧠 **Quiz interactivo:**",
        "quiz_correct": "✅ **¡Correcto!** Buen trabajo 🎉",
        "quiz_incorrect": "❌ **Incorrecto.** La opción correcta es: **{correct}**",
        "challenge_title": "🎯 **Tu reto diario:**",
        "stats_title": "📈 **Estadísticas:**",
        "vocab_count": "Frases guardadas",
        "settings_updated": "✅ ¡Ajustes actualizados!",
        "photo_processing": "🔍 <i>Reconociendo texto en la foto...</i>",
        "btn_repeat_audio": "🔊 Escuchar de nuevo",
        "btn_explain_grammar": "💡 Explicar gramática",
        "btn_save_phrase": "💾 Guardar frase",
        "reminder_set": "✅ ¡Recordatorio diario programado a las **{time}**!",
        "reminder_prompt": "⏰ **¡Pausa de estudio de 15 minutos!** Es hora de practicar con tu tutor de IA.",
        "daily_phrase_title": "🌟 **Frase del día (nivel {level}):**",
        "challenge_100_title": "🏆 **Reto de 100 días de aprendizaje:**",
        "recognized": "🗣 <i>Reconocido:</i> "
    },
    "it": {
        "welcome": "👋 Ciao! Configura il tuo profilo. Scegli la tua lingua madre:",
        "target": "Ottimo! Ora scegli la lingua che vuoi imparare:",
        "scenario": "Perfetto! Scegli uno scenario di comunicazione:",
        "done": "✅ Configurazione completata!\n\n💬 Ora puoi inviare messaggi di **testo**, 🎙️ registrare **messaggi vocali** o 📷 inviare **foto con testo** per la traduzione.\n\n👉 *Tocca il pulsante **Menu** accanto alla chat per vedere i comandi.*",
        "profile_title": "PASSAPORTO LINGUISTICO",
        "native_lang": "Madrelingua",
        "target_lang": "Lingua di studio",
        "scenario_label": "Scenario",
        "streak_label": "Serie",
        "level_label": "Livello",
        "msgs_label": "Messaggi inviati",
        "error": "Errore di connessione con l'IA.",
        "audio_error": "Errore audio.",
        "grammar_title": "💡 Spiegazione grammaticale:",
        "saved": "✅ Frase salvata nel vocabolario!",
        "profile_not_found": "Profilo non trovato. Digita /start",
        "vocabulary_title": "Il tuo vocabolario salvato:",
        "empty_vocabulary": "📭 Il tuo vocabolario è vuoto. Clicca su '💾 Salva frase' sotto i messaggi!",
        "deleted": "✅ Frase eliminata!",
        "settings_title": "⚙️ **Impostazioni profilo:**",
        "btn_native": "🌍 Madrelingua",
        "btn_target": "🎯 Lingua di studio",
        "btn_scenario": "🎭 Scenario",
        "level_title": "📊 Livello attuale: **{level}**.\nScegli il tuo nuovo livello:",
        "level_updated": "✅ Livello aggiornato a **{level}**!",
        "empty_vocab_quiz": "📭 Vocabolario vuoto! Salva prima almeno una frase.",
        "quiz_title": "🧠 **Quiz interattivo:**",
        "quiz_correct": "✅ **Corretto!** Ottimo lavoro 🎉",
        "quiz_incorrect": "❌ **Errato.** L'opzione corretta è: **{correct}**",
        "challenge_title": "🎯 **La tua sfida giornaliera:**",
        "stats_title": "📈 **Statistiche:**",
        "vocab_count": "Frasi salvate",
        "settings_updated": "✅ Impostazioni aggiornate!",
        "photo_processing": "🔍 <i>Riconoscimento del testo nella foto...</i>",
        "btn_repeat_audio": "🔊 Ascolta di nuovo",
        "btn_explain_grammar": "💡 Spiega grammatica",
        "btn_save_phrase": "💾 Salva frase",
        "reminder_set": "✅ Promemoria giornaliero impostato per le **{time}**!",
        "reminder_prompt": "⏰ **Pausa di studio di 15 minuti!** È ora di fare pratica con il tuo tutor IA.",
        "daily_phrase_title": "🌟 **Frase del giorno (livello {level}):**",
        "challenge_100_title": "🏆 **Sfida di 100 giorni di apprendimento:**",
        "recognized": "🗣 <i>Riconosciuto:</i> "
    },
    "ar": {
        "welcome": "👋 أهلاً! دعنا نعد ملفك الشخصي. اختر لغتك الأم:",
        "target": "رائع! الآن اختر اللغة التي تريد تعلمها:",
        "scenario": "ممتاز! اختر سيناريو التواصل:",
        "done": "✅ اكتمال الإعداد!\n\n💬 يمكنك الآن إرسال رسائل **نصية**، 🎙️ تسجيل **رسائل صوتية** أو 📷 إرسال **صور مع نص** للترجمة.\n\n👉 *انقر فوق زر **Menu** بجوار الدردشة لرؤية الأوامر.*",
        "profile_title": "جواز السفر اللغوي",
        "native_lang": "اللغة الأم",
        "target_lang": "لغة التعلم",
        "scenario_label": "السيناريو",
        "streak_label": "التتابع",
        "level_label": "المستوى",
        "msgs_label": "الرسائل المرسلة",
        "error": "عذراً، حدث خطأ أثناء الاتصال بالذكاء الاصطناعي.",
        "audio_error": "فشل إنشاء الصوت.",
        "grammar_title": "💡 شرح القواعد:",
        "saved": "✅ تم حفظ العبارة في مفرداتك بنجاح!",
        "profile_not_found": "الملف غير موجود. اكتب /start",
        "vocabulary_title": "مفرداتك المحفوظة:",
        "empty_vocabulary": "📭 مفرداتك فارغة بعد. انقر على '💾 حفظ العبارة' أسفل رسائل البوت!",
        "deleted": "✅ تم حذف العبارة!",
        "settings_title": "⚙️ **إعدادات الملف الشخصي:**",
        "btn_native": "🌍 اللغة الأم",
        "btn_target": "🎯 لغة التعلم",
        "btn_scenario": "🎭 السيناريو",
        "level_title": "📊 مستواك الحالي: **{level}**.\nاختر مستواك الجديد:",
        "level_updated": "✅ تم تحديث المستوى إلى **{level}** بنجاح!",
        "empty_vocab_quiz": "📭 مفرداتك فارغة! احفظ عبارة واحدة على الأقل أولاً.",
        "quiz_title": "🧠 **اختبار المفردات التفاعلي:**",
        "quiz_correct": "✅ **صحيح!** عمل رائع 🎉",
        "quiz_incorrect": "❌ **خطأ.** الخيار الصحيح هو: **{correct}**",
        "challenge_title": "🎯 **تحديك اليومي:**",
        "stats_title": "📈 **الإحصائيات:**",
        "vocab_count": "العبارات المحفوظة",
        "settings_updated": "✅ تم تحديث الإعدادات بنجاح!",
        "photo_processing": "🔍 <i>جاري التعرف على النص في الصورة وترجمته...</i>",
        "btn_repeat_audio": "🔊 استمع مرة أخرى",
        "btn_explain_grammar": "💡 اشرح القواعد",
        "btn_save_phrase": "💾 حفظ العبارة",
        "reminder_set": "✅ تم ضبط وقت التذكير اليومي على **{time}** بنجاح!",
        "reminder_prompt": "⏰ **وقت استراحة الدراسة لمدة 15 دقيقة!** حان الوقت لممارسة اللغات مع معلم الذكاء الاصطناعي الخاص بك.",
        "daily_phrase_title": "🌟 **عبارة اليوم (المستوى {level}):**",
        "challenge_100_title": "🏆 **تحدي الـ 100 يوم للتعلم:**",
        "recognized": "🗣 <i>تم التعرف على:</i> "
    }
}

# Состояния FSM
class Onboarding(StatesGroup):
    native = State()
    target = State()
    scenario = State()


# --- БАЗА ДАННЫХ (АВТОМИГРАЦИЯ) ---
def init_db():
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                native_language TEXT DEFAULT 'ru',
                target_language TEXT DEFAULT 'en',
                streak INTEGER DEFAULT 3,
                last_active TEXT DEFAULT '2026-10-02',
                messages_count INTEGER DEFAULT 0,
                scenario TEXT DEFAULT 'tutor',
                level TEXT DEFAULT 'B1',
                level_progress INTEGER DEFAULT 4,
                reminder_time TEXT DEFAULT '19:00',
                last_phrase_date TEXT DEFAULT ''
            )
        """)
        
        for col, col_type, default_val in [
            ("scenario", "TEXT", "tutor"),
            ("level", "TEXT", "B1"),
            ("level_progress", "INTEGER", "4"),
            ("reminder_time", "TEXT", "19:00"),
            ("last_phrase_date", "TEXT", "")
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type} DEFAULT '{default_val}'")
            except sqlite3.OperationalError:
                pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phrase TEXT
            )
        """)
        conn.commit()

def get_user(user_id: int):
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT native_language, target_language, streak, last_active, messages_count, scenario, level, level_progress, reminder_time, last_phrase_date FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    return row

def get_translation(user_id: int, key: str) -> str:
    user = get_user(user_id)
    native_lang = user[0] if user and user[0] in TRANSLATIONS else "ru"
    return TRANSLATIONS.get(native_lang, TRANSLATIONS["ru"]).get(key, key)


# --- ДИЗАЙН И КЛАВИАТУРЫ ---
def generate_progress_bar(current: int, total: int = 7, filled_emoji: str = "🟩", empty_emoji: str = "⬜") -> str:
    current = max(0, min(current, total))
    return filled_emoji * current + empty_emoji * (total - current)

def get_ai_response_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_translation(user_id, "btn_repeat_audio"), callback_data="repeat_audio")
    builder.button(text=get_translation(user_id, "btn_explain_grammar"), callback_data="explain_grammar")
    builder.button(text=get_translation(user_id, "btn_save_phrase"), callback_data="save_phrase")
    builder.adjust(2, 1)
    return builder.as_markup()


# --- ОНБОРДИНГ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    builder = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        builder.button(text=name, callback_data=f"native_{code}")
    builder.adjust(2)

    await state.set_state(Onboarding.native)
    await message.answer(
        "👋 Привет! Выбери свой родной язык / Вибери свою рідну мову / Choose your native language:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("native_"), Onboarding.native)
async def process_native(callback: types.CallbackQuery, state: FSMContext):
    native_code = callback.data.split("_")[1]
    user_id = callback.from_user.id

    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET native_language = ? WHERE user_id = ?", (native_code, user_id))
        conn.commit()

    builder = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        builder.button(text=name, callback_data=f"target_{code}")
    builder.adjust(2)

    msg = get_translation(user_id, "target")
    await state.set_state(Onboarding.target)
    await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("target_"), Onboarding.target)
async def process_target(callback: types.CallbackQuery, state: FSMContext):
    target_code = callback.data.split("_")[1]
    user_id = callback.from_user.id

    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET target_language = ? WHERE user_id = ?", (target_code, user_id))
        conn.commit()

    user_data = get_user(user_id)
    native_code = user_data[0] if user_data else "ru"
    msg = get_translation(user_id, "scenario")

    builder = InlineKeyboardBuilder()
    for sc_key in SCENARIOS:
        sc_text = SCENARIOS[sc_key].get(native_code, SCENARIOS[sc_key]["ru"])
        builder.button(text=sc_text, callback_data=f"scenario_{sc_key}")
    builder.adjust(1)

    await state.set_state(Onboarding.scenario)
    await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("scenario_"), Onboarding.scenario)
async def process_scenario(callback: types.CallbackQuery, state: FSMContext):
    scenario_key = callback.data.split("_")[1]
    user_id = callback.from_user.id

    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET scenario = ? WHERE user_id = ?", (scenario_key, user_id))
        conn.commit()

    msg = get_translation(user_id, "done")
    await state.clear()
    await callback.message.edit_text(msg, parse_mode="Markdown")
    await callback.answer()


# --- КОМАНДЫ: /settings, /level, /quiz, /challenge, /stats, /100days, /reminder ---

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    text = get_translation(user_id, "settings_title")
    builder = InlineKeyboardBuilder()
    builder.button(text=get_translation(user_id, "btn_native"), callback_data="set_native")
    builder.button(text=get_translation(user_id, "btn_target"), callback_data="set_target")
    builder.button(text=get_translation(user_id, "btn_scenario"), callback_data="set_scenario")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_native")
async def cb_set_native(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        builder.button(text=name, callback_data=f"upd_native_{code}")
    builder.adjust(2)
    user_id = callback.from_user.id
    await callback.message.edit_text(get_translation(user_id, "btn_native") + ":", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("upd_native_"))
async def cb_upd_native(callback: types.CallbackQuery):
    code = callback.data.split("_")[2]
    user_id = callback.from_user.id
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET native_language = ? WHERE user_id = ?", (code, user_id))
        conn.commit()
    await callback.message.edit_text(get_translation(user_id, "settings_updated"))
    await callback.answer()

@dp.callback_query(F.data == "set_target")
async def cb_set_target(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        builder.button(text=name, callback_data=f"upd_target_{code}")
    builder.adjust(2)
    user_id = callback.from_user.id
    await callback.message.edit_text(get_translation(user_id, "btn_target") + ":", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("upd_target_"))
async def cb_upd_target(callback: types.CallbackQuery):
    code = callback.data.split("_")[2]
    user_id = callback.from_user.id
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET target_language = ? WHERE user_id = ?", (code, user_id))
        conn.commit()
    await callback.message.edit_text(get_translation(user_id, "settings_updated"))
    await callback.answer()

@dp.callback_query(F.data == "set_scenario")
async def cb_set_scenario(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user(user_id)
    native_code = user_data[0] if user_data else "ru"
    builder = InlineKeyboardBuilder()
    for sc_key in SCENARIOS:
        sc_text = SCENARIOS[sc_key].get(native_code, SCENARIOS[sc_key]["ru"])
        builder.button(text=sc_text, callback_data=f"upd_scen_{sc_key}")
    builder.adjust(1)
    await callback.message.edit_text(get_translation(user_id, "btn_scenario") + ":", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("upd_scen_"))
async def cb_upd_scen(callback: types.CallbackQuery):
    sc_key = callback.data.split("_")[2]
    user_id = callback.from_user.id
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET scenario = ? WHERE user_id = ?", (sc_key, user_id))
        conn.commit()
    await callback.message.edit_text(get_translation(user_id, "settings_updated"))
    await callback.answer()


@dp.message(Command("level"))
async def cmd_level(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    current_level = user_data[6]
    text = get_translation(user_id, "level_title").format(level=current_level)
    
    builder = InlineKeyboardBuilder()
    for lvl in LEVELS:
        builder.button(text=f"📌 {lvl}", callback_data=f"set_lvl_{lvl}")
    builder.adjust(3)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("set_lvl_"))
async def cb_set_level(callback: types.CallbackQuery):
    lvl = callback.data.split("_")[2]
    user_id = callback.from_user.id
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (lvl, user_id))
        conn.commit()
    
    msg = get_translation(user_id, "level_updated").format(level=lvl)
    await callback.message.edit_text(msg, parse_mode="Markdown")
    await callback.answer()


# --- ИНТЕРАКТИВНЫЙ QUIZ ---

@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phrase FROM vocabulary WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()

    if not rows:
        await message.answer(get_translation(user_id, "empty_vocab_quiz"))
        return

    random_phrase = random.choice(rows)[0]
    target_code = user_data[1]
    native_code = user_data[0]
    target_lang_name = LANGUAGES.get(target_code, "English")
    native_lang_name = LANGUAGES.get(native_code, "Russian")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a language learning assistant. Create a multiple-choice quiz question with 4 options (A, B, C, D) based on the phrase. Write all questions and explanations strictly in the user's native language ({native_lang_name}). Follow strict formatting."},
                {"role": "user", "content": f"Phrase: '{random_phrase}'. Target language: {target_lang_name}. User native language: {native_lang_name}. "
                                           f"Format strictly like this:\n"
                                           f"QUESTION: [Question text or translation task in {native_lang_name}]\n"
                                           f"A) [Option 1]\n"
                                           f"B) [Option 2]\n"
                                           f"C) [Option 3]\n"
                                           f"D) [Option 4]\n"
                                           f"CORRECT: [a or b or c or d]"}
            ]
        )
        content = response.choices[0].message.content
        
        lines = content.strip().split("\n")
        q_lines = []
        correct_letter = "a"
        
        for line in lines:
            if line.startswith("QUESTION:") or line.startswith("A)") or line.startswith("B)") or line.startswith("C)") or line.startswith("D)"):
                q_lines.append(line)
            elif line.startswith("CORRECT:"):
                correct_letter = line.replace("CORRECT:", "").strip().lower()
        
        full_question = "\n".join(q_lines).replace("QUESTION:", "❓ **Question:**")
        correct_letter = correct_letter[0] if correct_letter else "a"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="A", callback_data=f"quiz_ans_a_{correct_letter}")
        builder.button(text="B", callback_data=f"quiz_ans_b_{correct_letter}")
        builder.button(text="C", callback_data=f"quiz_ans_c_{correct_letter}")
        builder.button(text="D", callback_data=f"quiz_ans_d_{correct_letter}")
        builder.adjust(2, 2)

        title = get_translation(user_id, "quiz_title")
        await message.answer(f"{title}\n\n💬 *Phrase:* {random_phrase}\n\n{full_question}", reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception as e:
        await message.answer(get_translation(user_id, "error"))


@dp.callback_query(F.data.startswith("quiz_ans_"))
async def process_quiz_answer(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    chosen = parts[2]
    correct = parts[3]
    user_id = callback.from_user.id
    
    if chosen == correct:
        ans_text = f"\n\n{get_translation(user_id, 'quiz_correct')}"
    else:
        incorrect_template = get_translation(user_id, 'quiz_incorrect')
        ans_text = f"\n\n{incorrect_template.format(correct=correct.upper())}"
    
    try:
        await callback.message.edit_text(f"{callback.message.text}{ans_text}", parse_mode="Markdown")
    except Exception:
        await callback.message.answer(ans_text)
    
    await callback.answer()


@dp.message(Command("challenge"))
async def cmd_challenge(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    target_code = user_data[1]
    native_code = user_data[0]
    target_lang_name = LANGUAGES.get(target_code, "English")
    native_lang_name = LANGUAGES.get(native_code, "Russian")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Give a short daily language learning challenge in {target_lang_name} with instructions and explanations strictly in the user's native language ({native_lang_name})."},
                {"role": "user", "content": "Give me a daily challenge."}
            ]
        )
        challenge_text = response.choices[0].message.content
    except Exception as e:
        challenge_text = "Write 3 sentences about your favorite hobby in your target language!"

    title = get_translation(user_id, "challenge_title")
    await message.answer(f"**{title}**\n\n{challenge_text}", parse_mode="Markdown")


# --- ЧЕЛЛЕНДЖ 100 ДНЕЙ ---
@dp.message(Command("100days"))
async def cmd_100days(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    streak = user_data[2]
    title = get_translation(user_id, "challenge_100_title")
    bar = generate_progress_bar(streak, total=100, filled_emoji="🔥", empty_emoji="⏳")
    text = (
        f"**{title}**\n\n"
        f"Streak: **{streak} / 100 days**!\n\n"
        f"{bar}\n\n"
        f"Practice every day for at least 15 minutes to reach your 100-day goal and level up your language proficiency!"
    )
    await message.answer(text, parse_mode="Markdown")


# --- НАПОМИНАНИЯ (15 МИНУТ ПАУЗА) ---
@dp.message(Command("reminder"))
async def cmd_reminder(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    args = message.text.split()
    if len(args) > 1:
        new_time = args[1]
        with sqlite3.connect("bot_database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET reminder_time = ? WHERE user_id = ?", (new_time, user_id))
            conn.commit()
        msg = get_translation(user_id, "reminder_set").format(time=new_time)
        await message.answer(msg, parse_mode="Markdown")
    else:
        current_time = user_data[8] if len(user_data) > 8 and user_data[8] else "19:00"
        await message.answer(
            f"⏰ Current reminder time: **{current_time}**.\n\n"
            f"To change your daily 15-minute study break reminder time, send the command like this:\n`/reminder 20:30`",
            parse_mode="Markdown"
        )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    nat_code, target_code, streak, last_active, msg_count, scenario, level, level_prog, reminder_time, _ = user_data
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE user_id = ?", (user_id,))
        vocab_count = cursor.fetchone()[0]

    title = get_translation(user_id, "stats_title")
    l_vocab = get_translation(user_id, "vocab_count")
    
    stats_text = (
        f"**{title}**\n\n"
        f"💬 Messages sent: **{msg_count}**\n"
        f"📚 {l_vocab}: **{vocab_count}**\n"
        f"🔥 Streak: **{streak} days**\n"
        f"📊 Level: **{level}**\n"
        f"⏰ Study reminder: **{reminder_time}**\n"
        f"🎧 Audio: **Active**\n"
    )
    await message.answer(stats_text, parse_mode="Markdown")


# --- ПРОФИЛЬ И СЛОВАРЬ ---

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Профиль не найден. Напиши /start")
        return
    
    nat_code, target_code, streak, last_active, msg_count, scenario, level, level_prog, _, _ = user_data
    nat_name = LANGUAGES.get(nat_code, nat_code)
    target_name = LANGUAGES.get(target_code, target_code)
    scen_name = SCENARIOS.get(scenario, {}).get(nat_code, scenario)
    
    streak_bar = generate_progress_bar(streak, total=7, filled_emoji="🟩", empty_emoji="⬜️")
    level_bar = generate_progress_bar(level_prog, total=7, filled_emoji="🟦", empty_emoji="⬜️")
    
    title = get_translation(user_id, "profile_title")
    l_native = get_translation(user_id, "native_lang")
    l_target = get_translation(user_id, "target_lang")
    l_scen = get_translation(user_id, "scenario_label")
    l_streak = get_translation(user_id, "streak_label")
    l_level = get_translation(user_id, "level_label")
    l_msgs = get_translation(user_id, "msgs_label")
    
    profile_card = (
        f"╔═══════════════════════════╗\n"
        f"║   🪪  **{title}**  🪪   ║\n"
        f"╚═══════════════════════════╝\n\n"
        f"🌍 **{l_native}:** {nat_name}\n"
        f"🎯 **{l_target}:** {target_name}\n"
        f"🎭 **{l_scen}:** {scen_name}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 **{l_streak} ({streak}):**\n{streak_bar}\n\n"
        f"📊 **{l_level} ({level}):**\n{level_bar}\n\n"
        f"💬 **{l_msgs}:** {msg_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(profile_card, parse_mode="Markdown")


@dp.message(Command("vocabulary"))
async def cmd_vocabulary(message: types.Message):
    user_id = message.from_user.id
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phrase FROM vocabulary WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()

    if not rows:
        await message.answer(get_translation(user_id, "empty_vocabulary"))
        return

    title = get_translation(user_id, "vocabulary_title")
    text = f"📚 **{title}**\n\n"
    
    builder = InlineKeyboardBuilder()
    for idx, (row_id, phrase) in enumerate(rows, 1):
        clean_phrase = phrase.replace("\n", " ")
        if len(clean_phrase) > 40:
            clean_phrase = clean_phrase[:37] + "..."
        text += f"{idx}. {clean_phrase}\n"
        builder.button(text=f"❌ #{idx}", callback_data=f"del_phrase_{row_id}")
    
    builder.adjust(4)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data.startswith("del_phrase_"))
async def process_delete_phrase(callback: types.CallbackQuery):
    phrase_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vocabulary WHERE id = ? AND user_id = ?", (phrase_id, user_id))
        conn.commit()
    
    await callback.answer(get_translation(user_id, "deleted"), show_alert=True)
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phrase FROM vocabulary WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()

    if not rows:
        await callback.message.edit_text(get_translation(user_id, "empty_vocabulary"))
        return

    title = get_translation(user_id, "vocabulary_title")
    text = f"📚 **{title}**\n\n"
    
    builder = InlineKeyboardBuilder()
    for idx, (row_id, phrase) in enumerate(rows, 1):
        clean_phrase = phrase.replace("\n", " ")
        if len(clean_phrase) > 40:
            clean_phrase = clean_phrase[:37] + "..."
        text += f"{idx}. {clean_phrase}\n"
        builder.button(text=f"❌ #{idx}", callback_data=f"del_phrase_{row_id}")
    
    builder.adjust(4)
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception:
        pass


# --- КНОПКИ ОТВЕТОВ ИИ ---

@dp.callback_query(F.data == "repeat_audio")
async def process_repeat_audio(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text_to_speech = callback.message.text or "Hello!"
    speech_file_name = f"repeat_{user_id}.mp3"
    
    await callback.answer("...")
    try:
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text_to_speech[:400]
        )
        speech_response.stream_to_file(speech_file_name)
        await callback.message.answer_voice(voice=FSInputFile(speech_file_name))
        if os.path.exists(speech_file_name):
            os.remove(speech_file_name)
    except Exception as e:
        await callback.answer(get_translation(user_id, "audio_error"), show_alert=True)

@dp.callback_query(F.data == "explain_grammar")
async def process_explain_grammar(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user(user_id)
    native_code = user_data[0] if user_data else "ru"
    native_lang_name = LANGUAGES.get(native_code, "Russian")
    target_text = callback.message.text
    
    await callback.answer("...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Explain the grammar, vocabulary, or structure of this text briefly and clearly strictly in the user's native language ({native_lang_name})."},
                {"role": "user", "content": target_text}
            ]
        )
        explanation = response.choices[0].message.content
        title = get_translation(user_id, "grammar_title")
        await callback.message.answer(f"**{title}**\n\n{explanation}", parse_mode="Markdown")
    except Exception as e:
        await callback.message.answer(get_translation(user_id, "error"))

@dp.callback_query(F.data == "save_phrase")
async def process_save_phrase(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phrase = callback.message.text
    
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vocabulary (user_id, phrase) VALUES (?, ?)", (user_id, phrase))
        conn.commit()
    
    success_msg = get_translation(user_id, "saved")
    await callback.answer(success_msg, show_alert=True)


# --- ОБРАБОТКА СООБЩЕНИЙ (ТЕКСТ, ГОЛОС И ФОТО) ---

async def process_ai_interaction(message: types.Message, user_id: int, user_text: str, user_data):
    native_code, target_code, streak, last_active, msg_count, scenario, level, level_prog, _, _ = user_data
    target_lang_name = LANGUAGES.get(target_code, "English")
    native_lang_name = LANGUAGES.get(native_code, "Russian")

    scenario_prompts = {
        "tutor": f"You are a helpful language tutor matching level {level}. Converse naturally in {target_lang_name}. If you need to explain grammar, translate, give instructions, or provide meta-commentary, you MUST use the user's native language ({native_lang_name}).",
        "translator": f"You act as a professional translator between {native_lang_name} and {target_lang_name}. Provide explanations strictly in {native_lang_name}.",
        "interview": f"Conduct a job interview in {target_lang_name} at level {level}. If feedback is needed, use {native_lang_name}.",
        "airport": f"You are airport staff or customs officer. Speak in {target_lang_name}.",
        "shop": f"You are a shop assistant helping a customer. Speak in {target_lang_name}.",
        "hospital": f"You are a doctor or medical receptionist. Speak in {target_lang_name}.",
        "restaurant": f"You are a waiter in a restaurant. Take the order and converse in {target_lang_name}.",
        "travel": f"You are a local tour guide or travel assistant. Speak in {target_lang_name}."
    }
    sys_prompt = scenario_prompts.get(scenario, scenario_prompts["tutor"])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        ai_reply = response.choices[0].message.content
    except Exception as e:
        ai_reply = get_translation(user_id, "error")

    speech_file_name = f"voice_{user_id}.mp3"
    try:
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=ai_reply[:400]
        )
        speech_response.stream_to_file(speech_file_name)
        await message.answer_voice(voice=FSInputFile(speech_file_name))
        if os.path.exists(speech_file_name):
            os.remove(speech_file_name)
    except Exception as e:
        pass

    await message.answer(ai_reply, reply_markup=get_ai_response_keyboard(user_id))

    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET messages_count = messages_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


@dp.message(F.text)
async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Please type /start")
        return
    await process_ai_interaction(message, user_id, message.text, user_data)


@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Please type /start")
        return

    voice_file_name = f"voice_in_{user_id}.ogg"
    try:
        file_info = await bot.get_file(message.voice.file_id)
        await bot.download_file(file_info.file_path, voice_file_name)
        
        with open(voice_file_name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        user_text = transcript.text
        
        if os.path.exists(voice_file_name):
            os.remove(voice_file_name)
    except Exception as e:
        await message.answer(get_translation(user_id, "error"))
        return

    rec_prefix = get_translation(user_id, "recognized")
    await message.answer(f"{rec_prefix}{user_text}", parse_mode="HTML")
    await process_ai_interaction(message, user_id, user_text, user_data)


@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Please type /start")
        return

    photo = message.photo[-1]
    photo_file_name = f"photo_{user_id}.jpg"
    
    try:
        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_info.file_path, photo_file_name)
        
        with open(photo_file_name, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        if os.path.exists(photo_file_name):
            os.remove(photo_file_name)
    except Exception as e:
        await message.answer(get_translation(user_id, "error"))
        return

    native_code, target_code, streak, last_active, msg_count, scenario, level, level_prog, _, _ = user_data
    target_lang_name = LANGUAGES.get(target_code, "German")
    native_lang_name = LANGUAGES.get(native_code, "Russian")

    processing_msg = get_translation(user_id, "photo_processing")
    await message.answer(processing_msg, parse_mode="HTML")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a language learning assistant. User's native language is {native_lang_name}, and target learning language is {target_lang_name} (Level: {level}). "
                                f"Analyze the text on the user's photo:\n"
                                f"1. If the text on the image is in {native_lang_name}, translate it into the target language ({target_lang_name}).\n"
                                f"2. If the text on the image is in {target_lang_name}, translate it into the user's native language ({native_lang_name}).\n"
                                f"3. Provide vocabulary and grammar explanations strictly in the user's native language ({native_lang_name})."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please analyze the text in this image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        ai_reply = response.choices[0].message.content
    except Exception as e:
        ai_reply = get_translation(user_id, "error")

    await message.answer(ai_reply, reply_markup=get_ai_response_keyboard(user_id))

    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET messages_count = messages_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


# --- ФОНОВЫЙ ПЛАНИРОВЩИК ---
async def background_scheduler(bot: Bot):
    while True:
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")
            
            with sqlite3.connect("bot_database.db") as conn:
                cursor = conn.cursor()
                
                # 1. Проверка напоминаний
                cursor.execute("SELECT user_id, reminder_time FROM users WHERE reminder_time = ?", (current_time_str,))
                reminder_users = cursor.fetchall()
                for u_id, _ in reminder_users:
                    try:
                        reminder_text = get_translation(u_id, "reminder_prompt")
                        await bot.send_message(u_id, f"⏰ {reminder_text}", parse_mode="Markdown")
                    except Exception as e:
                        logging.error(f"Failed to send reminder to {u_id}: {e}")
                
                # 2. Фраза дня (09:00)
                if current_time_str == "09:00":
                    cursor.execute("SELECT user_id, level, target_language, native_language, last_phrase_date FROM users")
                    all_users = cursor.fetchall()
                    for u_id, lvl, target_lang, native_lang, last_date in all_users:
                        if last_date != current_date_str:
                            try:
                                target_name = LANGUAGES.get(target_lang, "English")
                                native_name = LANGUAGES.get(native_lang, "Russian")
                                response = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {"role": "system", "content": f"Provide a useful phrase of the day in {target_name} for level {lvl} with translation and brief explanation strictly in the user's native language ({native_name})."},
                                        {"role": "user", "content": "Give me phrase of the day."}
                                    ]
                                )
                                phrase_content = response.choices[0].message.content
                                title_phrase = get_translation(u_id, "daily_phrase_title").format(level=lvl)
                                await bot.send_message(u_id, f"{title_phrase}\n\n{phrase_content}", parse_mode="Markdown")
                                
                                cursor.execute("UPDATE users SET last_phrase_date = ? WHERE user_id = ?", (current_date_str, u_id))
                                conn.commit()
                            except Exception as e:
                                logging.error(f"Failed to send daily phrase to {u_id}: {e}")
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        
        await asyncio.sleep(60)


# --- НАСТРОЙКА КНОПКИ MENU ---
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Начать настройку"),
        BotCommand(command="profile", description="🪪 Паспорт профиля"),
        BotCommand(command="vocabulary", description="📚 Личный словарь фраз"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="level", description="📊 Изменить уровень (A1-C2)"),
        BotCommand(command="quiz", description="🧠 Интерактивный квиз"),
        BotCommand(command="challenge", description="🎯 Ежедневный вызов"),
        BotCommand(command="100days", description="🏆 Челлендж 100 дней"),
        BotCommand(command="reminder", description="⏰ Напоминание 15 минут"),
        BotCommand(command="stats", description="📈 Статистика")
    ]
    await bot.set_my_commands(commands)


# --- ЗАПУСК БОТА ---
async def main():
    init_db()
    await set_bot_commands(bot)
    asyncio.create_task(background_scheduler(bot))
    logging.info("Бот запущен успешно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
