/**
 * Formatira ISO datum (YYYY-MM-DD) u srpski format DD.MM.YYYY.
 * Vraća '—' ako datum nije poznat, da ne bismo izmišljali datum.
 */
function formatDate(isoDate) {
    if (!isoDate) return '—';
    const parts = isoDate.split('-');
    if (parts.length !== 3) return isoDate;
    const [year, month, day] = parts;
    return `${day}.${month}.${year}.`;
}

/** Navigacija na klik cele kartice (koristi se umesto <a> da izbegnemo probleme sa dvostrukim klikom). */
function goTo(url) {
    window.location.href = url;
}
