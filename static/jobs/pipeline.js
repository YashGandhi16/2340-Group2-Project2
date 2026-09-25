(function () {
  const board = document.getElementById('pipeline-board');
  if (!board) return;

  const statusUrlTemplate = board.dataset.statusUrlTemplate;
  const csrfToken = board.dataset.csrfToken;
  const toast = document.getElementById('pipeline-toast');
  let draggedCard = null;
  let originColumn = null;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function () {
      toast.classList.remove('is-visible');
    }, 2200);
  }

  function updateCount(columnEl) {
    const countEl = columnEl.querySelector('.pipeline-count');
    const cards = columnEl.querySelectorAll('.pipeline-card').length;
    if (countEl) countEl.textContent = String(cards);
    const empty = columnEl.querySelector('.pipeline-empty');
    if (empty) {
      empty.hidden = cards > 0;
    }
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  board.querySelectorAll('.pipeline-card').forEach(function (card) {
    card.addEventListener('dragstart', function (event) {
      draggedCard = card;
      originColumn = card.closest('.pipeline-column');
      card.classList.add('is-dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.dataset.applicationId);
    });

    card.addEventListener('dragend', function () {
      card.classList.remove('is-dragging');
      board.querySelectorAll('.pipeline-column').forEach(function (col) {
        col.classList.remove('is-drop-target');
      });
      draggedCard = null;
      originColumn = null;
    });
  });

  board.querySelectorAll('.pipeline-column').forEach(function (column) {
    const dropZone = column.querySelector('.pipeline-cards');

    column.addEventListener('dragover', function (event) {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      column.classList.add('is-drop-target');
    });

    column.addEventListener('dragleave', function (event) {
      if (!column.contains(event.relatedTarget)) {
        column.classList.remove('is-drop-target');
      }
    });

    column.addEventListener('drop', function (event) {
      event.preventDefault();
      column.classList.remove('is-drop-target');
      if (!draggedCard) return;

      const card = draggedCard;
      const fromColumn = originColumn;
      const newStatus = column.dataset.status;
      const oldStatus = card.dataset.status;
      if (newStatus === oldStatus) return;

      dropZone.appendChild(card);
      if (fromColumn) updateCount(fromColumn);
      updateCount(column);

      const applicationId = card.dataset.applicationId;
      const url = statusUrlTemplate.replace('/0/', '/' + applicationId + '/');
      const body = new URLSearchParams();
      body.set('status', newStatus);

      fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken || getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: body,
      })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok || !result.data.ok) {
            throw new Error((result.data && result.data.error) || 'Update failed');
          }
          card.dataset.status = newStatus;
          showToast('Moved to ' + result.data.status_label);
        })
        .catch(function () {
          if (fromColumn) {
            fromColumn.querySelector('.pipeline-cards').appendChild(card);
            updateCount(fromColumn);
            updateCount(column);
          }
          showToast('Could not update status. Try again.');
        });
    });
  });

  const filter = document.getElementById('job-filter');
  if (filter) {
    filter.addEventListener('change', function () {
      const value = filter.value;
      const url = new URL(window.location.href);
      if (value) {
        url.searchParams.set('job', value);
      } else {
        url.searchParams.delete('job');
      }
      window.location.href = url.toString();
    });
  }
})();
