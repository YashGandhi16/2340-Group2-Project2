(function () {
  const board = document.getElementById('pipeline-board');

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
    if (countEl) {
      countEl.textContent = String(cards);
      countEl.setAttribute('aria-label', cards + ' applicants');
    }
    const empty = columnEl.querySelector('.pipeline-empty');
    if (empty) {
      empty.hidden = cards > 0;
    }
  }

  function syncMoveSelect(card) {
    const select = card.querySelector('[data-move-select]');
    if (!select) return;
    Array.prototype.forEach.call(select.options, function (option) {
      const label = option.textContent.replace(/^(Stage: |Move to )/, '');
      const current = option.value === card.dataset.status;
      option.textContent = (current ? 'Stage: ' : 'Move to ') + label;
      option.selected = current;
    });
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  // Move a card to another column optimistically, then persist; roll back on failure.
  function moveCard(card, column) {
    const fromColumn = card.closest('.pipeline-column');
    const newStatus = column.dataset.status;
    const oldStatus = card.dataset.status;
    if (newStatus === oldStatus) return;

    const dropZone = column.querySelector('.pipeline-cards');
    const emptyHint = dropZone.querySelector('.pipeline-empty');
    dropZone.insertBefore(card, emptyHint);
    if (fromColumn) updateCount(fromColumn);
    updateCount(column);
    card.classList.add('is-saving');

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
        syncMoveSelect(card);
        showToast('Moved to ' + result.data.status_label);
      })
      .catch(function () {
        if (fromColumn) {
          const originZone = fromColumn.querySelector('.pipeline-cards');
          originZone.insertBefore(card, originZone.querySelector('.pipeline-empty'));
          updateCount(fromColumn);
          updateCount(column);
        }
        syncMoveSelect(card);
        showToast('Could not update status. Try again.');
      })
      .finally(function () {
        card.classList.remove('is-saving');
      });
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

    // Keyboard / touch alternative to drag-and-drop.
    const select = card.querySelector('[data-move-select]');
    if (select) {
      select.addEventListener('change', function () {
        const target = board.querySelector('.pipeline-column[data-status="' + select.value + '"]');
        if (target) moveCard(card, target);
        select.focus();
      });
    }
  });

  board.querySelectorAll('.pipeline-column').forEach(function (column) {
    column.addEventListener('dragover', function (event) {
      if (!draggedCard) return;
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
      if (!draggedCard || column === originColumn) return;
      moveCard(draggedCard, column);
    });
  });
})();
