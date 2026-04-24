// ============================================================
// Claudia OS — Google Calendar (lectura + escritura)
// Pega este código en https://script.google.com
// Despliega como Web App con acceso "Cualquier persona" (Anyone)
// IMPORTANTE: en Configuración del proyecto → Zona horaria, elige la misma
// que tienes en user/config/settings.json (campo "timezone")
// ============================================================

// --- LECTURA (GET) ---

function doGet(e) {
  var days = e && e.parameter && e.parameter.days ? parseInt(e.parameter.days) : 1;
  if (isNaN(days) || days < 1) days = 1;
  if (days > 30) days = 30;

  var now = new Date();
  now.setHours(0, 0, 0, 0);
  var end = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);

  var calendars = CalendarApp.getAllCalendars();
  var allEvents = [];

  for (var i = 0; i < calendars.length; i++) {
    var cal = calendars[i];
    var events = cal.getEvents(now, end);

    for (var j = 0; j < events.length; j++) {
      var ev = events[j];
      allEvents.push({
        calendar: cal.getName(),
        calendarId: cal.getId(),
        title: ev.getTitle(),
        eventId: ev.getId(),
        start: ev.getStartTime().toISOString(),
        end: ev.getEndTime().toISOString(),
        allDay: ev.isAllDayEvent(),
        location: ev.getLocation() || null,
        description: ev.getDescription() || null
      });
    }
  }

  allEvents.sort(function(a, b) {
    return new Date(a.start) - new Date(b.start);
  });

  return ContentService
    .createTextOutput(JSON.stringify({ count: allEvents.length, events: allEvents }))
    .setMimeType(ContentService.MimeType.JSON);
}

// --- ESCRITURA (POST) ---

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var action = body.action;

    if (action === "create") return createEvent(body);
    if (action === "update") return updateEvent(body);
    if (action === "delete") return deleteEvent(body);
    if (action === "list_calendars") return listCalendars();

    return jsonResponse({ error: "Acción no reconocida: " + action });
  } catch (err) {
    return jsonResponse({ error: err.message });
  }
}

function createEvent(body) {
  var calId = body.calendarId;
  var cal = calId ? CalendarApp.getCalendarById(calId) : CalendarApp.getDefaultCalendar();
  if (!cal) return jsonResponse({ error: "Calendario no encontrado: " + calId });

  var ev;
  if (body.allDay) {
    var startDate = new Date(body.start);
    if (body.end) {
      var endDate = new Date(body.end);
      ev = cal.createAllDayEvent(body.title, startDate, endDate);
    } else {
      ev = cal.createAllDayEvent(body.title, startDate);
    }
  } else {
    var start = new Date(body.start);
    var end = new Date(body.end);
    ev = cal.createEvent(body.title, start, end);
  }

  if (body.location) ev.setLocation(body.location);
  if (body.description) ev.setDescription(body.description);

  return jsonResponse({
    ok: true,
    eventId: ev.getId(),
    calendar: cal.getName(),
    title: ev.getTitle(),
    start: ev.getStartTime().toISOString(),
    end: ev.getEndTime().toISOString()
  });
}

function updateEvent(body) {
  var ev = findEvent(body.calendarId, body.eventId);
  if (!ev) return jsonResponse({ error: "Evento no encontrado" });

  if (body.title) ev.setTitle(body.title);
  if (body.location !== undefined) ev.setLocation(body.location || "");
  if (body.description !== undefined) ev.setDescription(body.description || "");

  if (body.start && body.end) {
    if (body.allDay) {
      ev.setAllDayDate(new Date(body.start));
    } else {
      ev.setTime(new Date(body.start), new Date(body.end));
    }
  }

  return jsonResponse({
    ok: true,
    eventId: ev.getId(),
    title: ev.getTitle(),
    start: ev.getStartTime().toISOString(),
    end: ev.getEndTime().toISOString()
  });
}

function deleteEvent(body) {
  var ev = findEvent(body.calendarId, body.eventId);
  if (!ev) return jsonResponse({ error: "Evento no encontrado" });

  var title = ev.getTitle();
  ev.deleteEvent();

  return jsonResponse({ ok: true, deleted: title });
}

function listCalendars() {
  var calendars = CalendarApp.getAllCalendars();
  var result = [];
  for (var i = 0; i < calendars.length; i++) {
    var cal = calendars[i];
    result.push({
      name: cal.getName(),
      id: cal.getId(),
      isOwned: cal.isOwnedByMe()
    });
  }
  return jsonResponse({ calendars: result });
}

// --- Helpers ---

function findEvent(calendarId, eventId) {
  var cal = calendarId
    ? CalendarApp.getCalendarById(calendarId)
    : CalendarApp.getDefaultCalendar();
  if (!cal) return null;
  return cal.getEventById(eventId);
}

function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
