//! Localised strings for Rust-side task notifications.
//!
//! This table intentionally owns the small subset of notification strings
//! required while the WebView is destroyed.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TaskNotificationTexts {
    pub download_start_title: &'static str,
    pub download_start_body: &'static str,
    pub download_batch_start_body: &'static str,
    pub download_complete_title: &'static str,
    pub download_complete_body: &'static str,
    pub bt_complete_title: &'static str,
    pub bt_complete_body: &'static str,
    pub ed2k_complete_title: &'static str,
    pub ed2k_complete_body: &'static str,
    pub download_failed_title: &'static str,
    pub download_failed_body: &'static str,
    pub error_unknown: &'static str,
}

const EN_US_TEXTS: TaskNotificationTexts = TaskNotificationTexts {
    download_start_title: "Download Started",
    download_start_body: "Downloading: {taskName}",
    download_batch_start_body: "Downloading: {taskName} and {count} other task(s)",
    download_complete_title: "Download Complete",
    download_complete_body: "Saved: {taskName}",
    bt_complete_title: "BT Download Complete",
    bt_complete_body: "Seeding: {taskName}",
    ed2k_complete_title: "ED2K Download Complete",
    ed2k_complete_body: "Sharing: {taskName}",
    download_failed_title: "Download Failed",
    download_failed_body: "{taskName}: {reason}",
    error_unknown: "Unknown error",
};

#[cfg(test)]
const SUPPORTED_LOCALES: &[&str] = &[
    "ar", "bg", "ca", "de", "el", "en-US", "es", "fa", "fr", "hu", "hi", "id", "it", "ja", "ko",
    "nb", "nl", "pl", "pt-BR", "ro", "ru", "th", "tr", "uk", "vi", "zh-CN", "zh-TW",
];

pub fn resolve_supported_locale(raw_locale: &str) -> &'static str {
    let locale = raw_locale.trim();
    if locale.is_empty() || locale == "auto" {
        return "en-US";
    }

    match locale {
        "ar" => "ar",
        "bg" => "bg",
        "ca" => "ca",
        "de" => "de",
        "el" => "el",
        "en-US" => "en-US",
        "es" => "es",
        "fa" => "fa",
        "fr" => "fr",
        "hu" => "hu",
        "hi" => "hi",
        "id" => "id",
        "it" => "it",
        "ja" => "ja",
        "ko" => "ko",
        "nb" => "nb",
        "nl" => "nl",
        "pl" => "pl",
        "pt-BR" => "pt-BR",
        "ro" => "ro",
        "ru" => "ru",
        "th" => "th",
        "tr" => "tr",
        "uk" => "uk",
        "vi" => "vi",
        "zh-CN" => "zh-CN",
        "zh-TW" => "zh-TW",
        _ if locale.starts_with("ar") => "ar",
        _ if locale.starts_with("de") => "de",
        _ if locale.starts_with("en") => "en-US",
        _ if locale.starts_with("es") => "es",
        _ if locale.starts_with("fr") => "fr",
        _ if locale.starts_with("hi") => "hi",
        _ if locale.starts_with("it") => "it",
        _ if locale.starts_with("pt") => "pt-BR",
        "zh-HK" => "zh-TW",
        _ if locale.starts_with("zh") => "zh-CN",
        _ => "en-US",
    }
}

pub fn texts_for_locale(locale: &str) -> TaskNotificationTexts {
    match resolve_supported_locale(locale) {
        "ar" => TaskNotificationTexts {
            download_start_title: "بدء التنزيل",
            download_start_body: "جارٍ التنزيل: {taskName}",
            download_batch_start_body: "جارٍ التنزيل: {taskName} و{count} مهمة أخرى",
            download_complete_title: "اكتمل التنزيل",
            download_complete_body: "تم الحفظ: {taskName}",
            bt_complete_title: "اكتمل تنزيل BT",
            bt_complete_body: "جارٍ البذر: {taskName}",
            ed2k_complete_title: "اكتمل تنزيل ED2K",
            ed2k_complete_body: "جارٍ المشاركة: {taskName}",
            download_failed_title: "فشل التنزيل",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "bg" => TaskNotificationTexts {
            download_start_title: "Изтеглянето започна",
            download_start_body: "Изтегляне: {taskName}",
            download_batch_start_body: "Изтегляне: {taskName} и {count} други задачи",
            download_complete_title: "Изтеглянето е завършено",
            download_complete_body: "Запазено: {taskName}",
            bt_complete_title: "BT изтеглянето е завършено",
            bt_complete_body: "Споделяне: {taskName}",
            ed2k_complete_title: "ED2K изтеглянето е завършено",
            ed2k_complete_body: "Споделяне: {taskName}",
            download_failed_title: "Изтеглянето е неуспешно",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "ca" => TaskNotificationTexts {
            download_start_title: "Descàrrega iniciada",
            download_start_body: "Descarregant: {taskName}",
            download_batch_start_body: "Descarregant: {taskName} i {count} tasques més",
            download_complete_title: "Descàrrega completada",
            download_complete_body: "Desat: {taskName}",
            bt_complete_title: "Descàrrega BT completada",
            bt_complete_body: "Compartint: {taskName}",
            ed2k_complete_title: "Descàrrega ED2K completada",
            ed2k_complete_body: "Compartint: {taskName}",
            download_failed_title: "Descàrrega fallida",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "de" => TaskNotificationTexts {
            download_start_title: "Download gestartet",
            download_start_body: "Wird heruntergeladen: {taskName}",
            download_batch_start_body:
                "Wird heruntergeladen: {taskName} und {count} weitere Aufgaben",
            download_complete_title: "Download abgeschlossen",
            download_complete_body: "Gespeichert: {taskName}",
            bt_complete_title: "BT-Download abgeschlossen",
            bt_complete_body: "Seeding: {taskName}",
            ed2k_complete_title: "ED2K-Download abgeschlossen",
            ed2k_complete_body: "Teilen: {taskName}",
            download_failed_title: "Download fehlgeschlagen",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "el" => TaskNotificationTexts {
            download_start_title: "Η λήψη ξεκίνησε",
            download_start_body: "Γίνεται λήψη: {taskName}",
            download_batch_start_body: "Γίνεται λήψη: {taskName} και {count} ακόμα εργασίες",
            download_complete_title: "Η λήψη ολοκληρώθηκε",
            download_complete_body: "Αποθηκεύτηκε: {taskName}",
            bt_complete_title: "Η BT λήψη ολοκληρώθηκε",
            bt_complete_body: "Διαμοίραση: {taskName}",
            ed2k_complete_title: "Η ED2K λήψη ολοκληρώθηκε",
            ed2k_complete_body: "Κοινή χρήση: {taskName}",
            download_failed_title: "Η λήψη απέτυχε",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "es" => TaskNotificationTexts {
            download_start_title: "Descarga iniciada",
            download_start_body: "Descargando: {taskName}",
            download_batch_start_body: "Descargando: {taskName} y {count} tareas más",
            download_complete_title: "Descarga completada",
            download_complete_body: "Guardado: {taskName}",
            bt_complete_title: "Descarga BT completada",
            bt_complete_body: "Seeding: {taskName}",
            ed2k_complete_title: "Descarga ED2K completada",
            ed2k_complete_body: "Compartiendo: {taskName}",
            download_failed_title: "Descarga fallida",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "fa" => TaskNotificationTexts {
            download_start_title: "دانلود شروع شد",
            download_start_body: "در حال دانلود: {taskName}",
            download_batch_start_body: "در حال دانلود: {taskName} و {count} وظیفه دیگر",
            download_complete_title: "دانلود تکمیل شد",
            download_complete_body: "ذخیره شد: {taskName}",
            bt_complete_title: "دانلود BT تکمیل شد",
            bt_complete_body: "در حال بذرگذاری: {taskName}",
            ed2k_complete_title: "دانلود ED2K تکمیل شد",
            ed2k_complete_body: "در حال اشتراک‌گذاری: {taskName}",
            download_failed_title: "دانلود ناموفق بود",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "fr" => TaskNotificationTexts {
            download_start_title: "Téléchargement démarré",
            download_start_body: "Téléchargement: {taskName}",
            download_batch_start_body: "Téléchargement: {taskName} et {count} autres tâches",
            download_complete_title: "Téléchargement terminé",
            download_complete_body: "Enregistré: {taskName}",
            bt_complete_title: "Téléchargement BT terminé",
            bt_complete_body: "Partage: {taskName}",
            ed2k_complete_title: "Téléchargement ED2K terminé",
            ed2k_complete_body: "Partage: {taskName}",
            download_failed_title: "Échec du téléchargement",
            download_failed_body: "{taskName} : {reason}",
            error_unknown: "Unknown error",
        },
        "hu" => TaskNotificationTexts {
            download_start_title: "Letöltés elindult",
            download_start_body: "Letöltés: {taskName}",
            download_batch_start_body: "Letöltés: {taskName} és {count} további feladat",
            download_complete_title: "Letöltés befejezve",
            download_complete_body: "Mentve: {taskName}",
            bt_complete_title: "BT letöltés befejezve",
            bt_complete_body: "Megosztás: {taskName}",
            ed2k_complete_title: "ED2K letöltés befejezve",
            ed2k_complete_body: "Megosztás: {taskName}",
            download_failed_title: "Letöltés sikertelen",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "hi" => TaskNotificationTexts {
            download_start_title: "डाउनलोड शुरू हुआ",
            download_start_body: "डाउनलोड हो रहा है: {taskName}",
            download_batch_start_body: "डाउनलोड हो रहा है: {taskName} और {count} अन्य task(s)",
            download_complete_title: "डाउनलोड पूरा हुआ",
            download_complete_body: "सहेजा गया: {taskName}",
            bt_complete_title: "BT डाउनलोड पूरा हुआ",
            bt_complete_body: "Seeding: {taskName}",
            ed2k_complete_title: "ED2K डाउनलोड पूरा हुआ",
            ed2k_complete_body: "Sharing: {taskName}",
            download_failed_title: "डाउनलोड विफल",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "अज्ञात त्रुटि",
        },
        "id" => TaskNotificationTexts {
            download_start_title: "Unduhan dimulai",
            download_start_body: "Mengunduh: {taskName}",
            download_batch_start_body: "Mengunduh: {taskName} dan {count} tugas lainnya",
            download_complete_title: "Unduhan selesai",
            download_complete_body: "Disimpan: {taskName}",
            bt_complete_title: "Unduhan BT selesai",
            bt_complete_body: "Seeding: {taskName}",
            ed2k_complete_title: "Unduhan ED2K selesai",
            ed2k_complete_body: "Berbagi: {taskName}",
            download_failed_title: "Unduhan gagal",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "it" => TaskNotificationTexts {
            download_start_title: "Download avviato",
            download_start_body: "Download in corso: {taskName}",
            download_batch_start_body: "Download in corso: {taskName} e altre {count} attività",
            download_complete_title: "Download completato",
            download_complete_body: "Salvato: {taskName}",
            bt_complete_title: "Download BT completato",
            bt_complete_body: "Condivisione: {taskName}",
            ed2k_complete_title: "Download ED2K completato",
            ed2k_complete_body: "Condivisione: {taskName}",
            download_failed_title: "Download non riuscito",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "ja" => TaskNotificationTexts {
            download_start_title: "ダウンロード開始",
            download_start_body: "ダウンロード中：{taskName}",
            download_batch_start_body: "ダウンロード中：{taskName} 他 {count} 件",
            download_complete_title: "ダウンロード完了",
            download_complete_body: "保存しました：{taskName}",
            bt_complete_title: "BT ダウンロード完了",
            bt_complete_body: "シード中：{taskName}",
            ed2k_complete_title: "ED2K ダウンロード完了",
            ed2k_complete_body: "共有中：{taskName}",
            download_failed_title: "ダウンロード失敗",
            download_failed_body: "{taskName}：{reason}",
            error_unknown: "不明なエラー",
        },
        "ko" => TaskNotificationTexts {
            download_start_title: "다운로드 시작",
            download_start_body: "다운로드 중: {taskName}",
            download_batch_start_body: "다운로드 중: {taskName} 외 {count}개",
            download_complete_title: "다운로드 완료",
            download_complete_body: "저장됨: {taskName}",
            bt_complete_title: "BT 다운로드 완료",
            bt_complete_body: "시딩 중: {taskName}",
            ed2k_complete_title: "ED2K 다운로드 완료",
            ed2k_complete_body: "공유 중: {taskName}",
            download_failed_title: "다운로드 실패",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "알 수 없는 오류",
        },
        "nb" => TaskNotificationTexts {
            download_start_title: "Nedlasting startet",
            download_start_body: "Laster ned: {taskName}",
            download_batch_start_body: "Laster ned: {taskName} og {count} andre oppgaver",
            download_complete_title: "Nedlasting fullført",
            download_complete_body: "Lagret: {taskName}",
            bt_complete_title: "BT-nedlasting fullført",
            bt_complete_body: "Deler: {taskName}",
            ed2k_complete_title: "ED2K-nedlasting fullført",
            ed2k_complete_body: "Deler: {taskName}",
            download_failed_title: "Nedlasting mislyktes",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "nl" => TaskNotificationTexts {
            download_start_title: "Download gestart",
            download_start_body: "Downloaden: {taskName}",
            download_batch_start_body: "Downloaden: {taskName} en {count} andere taken",
            download_complete_title: "Download voltooid",
            download_complete_body: "Opgeslagen: {taskName}",
            bt_complete_title: "BT-download voltooid",
            bt_complete_body: "Seeden: {taskName}",
            ed2k_complete_title: "ED2K-download voltooid",
            ed2k_complete_body: "Delen: {taskName}",
            download_failed_title: "Download mislukt",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "pl" => TaskNotificationTexts {
            download_start_title: "Pobieranie rozpoczęte",
            download_start_body: "Pobieranie: {taskName}",
            download_batch_start_body: "Pobieranie: {taskName} i {count} innych zadań",
            download_complete_title: "Pobieranie ukończone",
            download_complete_body: "Zapisano: {taskName}",
            bt_complete_title: "Pobieranie BT ukończone",
            bt_complete_body: "Udostępnianie: {taskName}",
            ed2k_complete_title: "Pobieranie ED2K ukończone",
            ed2k_complete_body: "Udostępnianie: {taskName}",
            download_failed_title: "Pobieranie nie powiodło się",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "pt-BR" => TaskNotificationTexts {
            download_start_title: "Download iniciado",
            download_start_body: "Baixando: {taskName}",
            download_batch_start_body: "Baixando: {taskName} e {count} outras tarefas",
            download_complete_title: "Download concluído",
            download_complete_body: "Salvo: {taskName}",
            bt_complete_title: "Download BT concluído",
            bt_complete_body: "Semeando: {taskName}",
            ed2k_complete_title: "Download ED2K concluído",
            ed2k_complete_body: "Compartilhando: {taskName}",
            download_failed_title: "Download falhou",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "ro" => TaskNotificationTexts {
            download_start_title: "Descărcare începută",
            download_start_body: "Se descarcă: {taskName}",
            download_batch_start_body: "Se descarcă: {taskName} și alte {count} sarcini",
            download_complete_title: "Descărcare finalizată",
            download_complete_body: "Salvat: {taskName}",
            bt_complete_title: "Descărcare BT finalizată",
            bt_complete_body: "Se distribuie: {taskName}",
            ed2k_complete_title: "Descărcare ED2K finalizată",
            ed2k_complete_body: "Se distribuie: {taskName}",
            download_failed_title: "Descărcarea a eșuat",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "ru" => TaskNotificationTexts {
            download_start_title: "Загрузка начата",
            download_start_body: "Загрузка: {taskName}",
            download_batch_start_body: "Загрузка: {taskName} и ещё {count} задач",
            download_complete_title: "Загрузка завершена",
            download_complete_body: "Сохранено: {taskName}",
            bt_complete_title: "BT-загрузка завершена",
            bt_complete_body: "Раздача: {taskName}",
            ed2k_complete_title: "ED2K-загрузка завершена",
            ed2k_complete_body: "Раздача: {taskName}",
            download_failed_title: "Загрузка не удалась",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "th" => TaskNotificationTexts {
            download_start_title: "เริ่มดาวน์โหลดแล้ว",
            download_start_body: "กำลังดาวน์โหลด: {taskName}",
            download_batch_start_body: "กำลังดาวน์โหลด: {taskName} และอีก {count} งาน",
            download_complete_title: "ดาวน์โหลดเสร็จสิ้น",
            download_complete_body: "บันทึกแล้ว: {taskName}",
            bt_complete_title: "ดาวน์โหลด BT เสร็จสิ้น",
            bt_complete_body: "กำลังแชร์: {taskName}",
            ed2k_complete_title: "ดาวน์โหลด ED2K เสร็จสิ้น",
            ed2k_complete_body: "กำลังแชร์: {taskName}",
            download_failed_title: "ดาวน์โหลดไม่สำเร็จ",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "tr" => TaskNotificationTexts {
            download_start_title: "İndirme başladı",
            download_start_body: "İndiriliyor: {taskName}",
            download_batch_start_body: "İndiriliyor: {taskName} ve {count} diğer görev",
            download_complete_title: "İndirme tamamlandı",
            download_complete_body: "Kaydedildi: {taskName}",
            bt_complete_title: "BT indirmesi tamamlandı",
            bt_complete_body: "Paylaşılıyor: {taskName}",
            ed2k_complete_title: "ED2K indirmesi tamamlandı",
            ed2k_complete_body: "Paylaşılıyor: {taskName}",
            download_failed_title: "İndirme başarısız",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "uk" => TaskNotificationTexts {
            download_start_title: "Завантаження розпочато",
            download_start_body: "Завантаження: {taskName}",
            download_batch_start_body: "Завантаження: {taskName} та ще {count} завдань",
            download_complete_title: "Завантаження завершено",
            download_complete_body: "Збережено: {taskName}",
            bt_complete_title: "BT-завантаження завершено",
            bt_complete_body: "Роздача: {taskName}",
            ed2k_complete_title: "ED2K-завантаження завершено",
            ed2k_complete_body: "Роздача: {taskName}",
            download_failed_title: "Завантаження не вдалося",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "vi" => TaskNotificationTexts {
            download_start_title: "Tải xuống đã bắt đầu",
            download_start_body: "Đang tải: {taskName}",
            download_batch_start_body: "Đang tải: {taskName} và {count} tác vụ khác",
            download_complete_title: "Tải xuống hoàn thành",
            download_complete_body: "Đã lưu: {taskName}",
            bt_complete_title: "Tải BT hoàn thành",
            bt_complete_body: "Đang seeding: {taskName}",
            ed2k_complete_title: "Tải ED2K hoàn thành",
            ed2k_complete_body: "Đang chia sẻ: {taskName}",
            download_failed_title: "Tải xuống thất bại",
            download_failed_body: "{taskName}: {reason}",
            error_unknown: "Unknown error",
        },
        "zh-CN" => TaskNotificationTexts {
            download_start_title: "下载已开始",
            download_start_body: "下载中：{taskName}",
            download_batch_start_body: "下载中：{taskName} 等 {count} 个任务",
            download_complete_title: "下载完成",
            download_complete_body: "已保存：{taskName}",
            bt_complete_title: "BT 下载完成",
            bt_complete_body: "做种中：{taskName}",
            ed2k_complete_title: "ED2K 下载完成",
            ed2k_complete_body: "共享中：{taskName}",
            download_failed_title: "下载失败",
            download_failed_body: "{taskName}：{reason}",
            error_unknown: "未知错误",
        },
        "zh-TW" => TaskNotificationTexts {
            download_start_title: "下載已開始",
            download_start_body: "下載中：{taskName}",
            download_batch_start_body: "下載中：{taskName} 等 {count} 個任務",
            download_complete_title: "下載完成",
            download_complete_body: "已儲存：{taskName}",
            bt_complete_title: "BT 下載完成",
            bt_complete_body: "做種中：{taskName}",
            ed2k_complete_title: "ED2K 下載完成",
            ed2k_complete_body: "共享中：{taskName}",
            download_failed_title: "下載失敗",
            download_failed_body: "{taskName}：{reason}",
            error_unknown: "未知錯誤",
        },
        _ => EN_US_TEXTS,
    }
}

pub fn format_task_message(template: &str, task_name: &str) -> String {
    template.replace("{taskName}", task_name)
}

pub fn format_error_message(template: &str, task_name: &str, reason: &str) -> String {
    template
        .replace("{taskName}", task_name)
        .replace("{reason}", reason)
}

pub fn format_batch_task_message(template: &str, task_name: &str, count: usize) -> String {
    template
        .replace("{taskName}", task_name)
        .replace("{count}", &count.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_explicit_supported_locale() {
        assert_eq!(resolve_supported_locale("zh-CN"), "zh-CN");
    }

    #[test]
    fn resolves_language_prefix_locale() {
        assert_eq!(resolve_supported_locale("zh-Hans-CN"), "zh-CN");
        assert_eq!(resolve_supported_locale("en-AU"), "en-US");
        assert_eq!(resolve_supported_locale("pt-PT"), "pt-BR");
        assert_eq!(resolve_supported_locale("hi-IN"), "hi");
    }

    #[test]
    fn falls_back_to_en_us_for_auto_or_unknown_locale() {
        assert_eq!(resolve_supported_locale("auto"), "en-US");
        assert_eq!(resolve_supported_locale("xx-YY"), "en-US");
    }

    #[test]
    fn all_supported_locales_have_notification_texts() {
        assert_eq!(SUPPORTED_LOCALES.len(), 27);
        for locale in SUPPORTED_LOCALES {
            let texts = texts_for_locale(locale);
            assert!(
                !texts.download_start_title.is_empty(),
                "empty start title for {locale}"
            );
            assert!(
                texts.download_start_body.contains("{taskName}"),
                "start body lacks placeholder for {locale}"
            );
            assert!(
                texts.download_batch_start_body.contains("{taskName}"),
                "batch start body lacks task placeholder for {locale}"
            );
            assert!(
                texts.download_batch_start_body.contains("{count}"),
                "batch start body lacks count placeholder for {locale}"
            );
            assert!(
                !texts.download_complete_title.is_empty(),
                "empty complete title for {locale}"
            );
            assert!(
                texts.download_complete_body.contains("{taskName}"),
                "complete body lacks placeholder for {locale}"
            );
            assert!(
                !texts.bt_complete_title.is_empty(),
                "empty BT title for {locale}"
            );
            assert!(
                texts.bt_complete_body.contains("{taskName}"),
                "BT body lacks placeholder for {locale}"
            );
            assert!(
                !texts.ed2k_complete_title.is_empty(),
                "empty ED2K title for {locale}"
            );
            assert!(
                texts.ed2k_complete_body.contains("{taskName}"),
                "ED2K body lacks placeholder for {locale}"
            );
            assert!(
                !texts.download_failed_title.is_empty(),
                "empty failed title for {locale}"
            );
            assert!(
                texts.download_failed_body.contains("{taskName}"),
                "failed body lacks placeholder for {locale}"
            );
            assert!(
                texts.download_failed_body.contains("{reason}"),
                "failed body lacks reason placeholder for {locale}"
            );
            assert!(
                !texts.error_unknown.is_empty(),
                "empty unknown error for {locale}"
            );
        }
    }

    #[test]
    fn localises_download_complete_texts() {
        let texts = texts_for_locale("en-US");
        assert_eq!(texts.download_complete_title, "Download Complete");
        assert_eq!(
            format_task_message(texts.download_complete_body, "file.zip"),
            "Saved: file.zip"
        );
    }

    #[test]
    fn localises_download_start_texts() {
        let texts = texts_for_locale("en-US");
        assert_eq!(texts.download_start_title, "Download Started");
        assert_eq!(
            format_task_message(texts.download_start_body, "file.zip"),
            "Downloading: file.zip"
        );
        assert_eq!(
            format_batch_task_message(texts.download_batch_start_body, "file.zip", 2),
            "Downloading: file.zip and 2 other task(s)"
        );
    }

    #[test]
    fn localises_bt_complete_texts() {
        let texts = texts_for_locale("en-US");
        assert_eq!(texts.bt_complete_title, "BT Download Complete");
        assert_eq!(
            format_task_message(texts.bt_complete_body, "file.zip"),
            "Seeding: file.zip"
        );
    }

    #[test]
    fn localises_ed2k_complete_texts() {
        let texts = texts_for_locale("zh-CN");
        assert_eq!(texts.ed2k_complete_title, "ED2K 下载完成");
        assert_eq!(
            format_task_message(texts.ed2k_complete_body, "file.zip"),
            "共享中：file.zip"
        );
    }

    #[test]
    fn localises_error_texts() {
        let texts = texts_for_locale("en-US");
        assert_eq!(
            format_error_message(texts.download_failed_body, "file.zip", "Network error"),
            "file.zip: Network error"
        );
    }
}
