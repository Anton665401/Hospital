// Проверка загрузки скрипта
console.log("script.js загружен");

// Функция для генерации временных слотов
function generateTimeSlots() {
    const timeSelect = document.getElementById('appointmentTime');
    if (!timeSelect) {
        console.error("Элемент appointmentTime не найден");
        return;
    }
    
    timeSelect.innerHTML = '<option value="">Выберите время</option>';
    
    // Генерируем слоты времени с 8:00 до 17:00
    for (let hour = 8; hour < 17; hour++) {
        const time = `${hour.toString().padStart(2, '0')}:00`;
        const option = document.createElement('option');
        option.value = time;
        option.textContent = time;
        timeSelect.appendChild(option);
    }
}

// Функция открытия модального окна
function openModal(doctorType) {
    console.log("Открытие модального окна для врача:", doctorType);
    
    const modal = document.getElementById('appointmentModal');
    const specialistSelect = document.getElementById('specialist');
    const dateInput = document.getElementById('appointmentDate');
    
    if (!modal) {
        console.error("Модальное окно не найдено");
        return;
    }
    
    if (!specialistSelect) {
        console.error("Поле выбора специалиста не найдено");
        return;
    }
    
    if (!dateInput) {
        console.error("Поле выбора даты не найдено");
        return;
    }
    
    // Устанавливаем и блокируем выбор специалиста
    if (doctorType) {
        specialistSelect.value = doctorType;
        specialistSelect.disabled = true;
        console.log("Специалист установлен:", doctorType);
    } else {
        specialistSelect.disabled = false;
    }
    
    // Устанавливаем минимальную дату - сегодня
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
    
    // Показываем модальное окно
    modal.style.display = 'block';
    
    // Генерируем временные слоты
    generateTimeSlots();
    console.log("Модальное окно открыто");
}

// Функция закрытия модального окна
function closeModal() {
    const modal = document.getElementById('appointmentModal');
    const form = document.getElementById('appointmentForm');
    const specialistSelect = document.getElementById('specialist');
    const successMessage = document.getElementById('successMessage');
    
    if (!modal || !form || !specialistSelect) {
        console.error("Не найдены необходимые элементы для закрытия");
        return;
    }
    
    // Очищаем форму и разблокируем поле выбора специалиста
    specialistSelect.disabled = false;
    form.reset();
    
    // Скрываем сообщение об успехе, если оно есть
    if (successMessage) {
        successMessage.style.display = 'none';
    }
    
    // Скрываем модальное окно
    modal.style.display = 'none';
}

// Обработка отправки формы
function submitForm(event) {
    event.preventDefault();

    // Получаем данные формы
    const policy = document.getElementById('policy').value;
    const specialist = document.getElementById('specialist').value;
    const date = document.getElementById('appointmentDate').value;
    const time = document.getElementById('appointmentTime').value;

    // Валидация
    if (!policy || !specialist || !date || !time) {
        alert('Пожалуйста, заполните все обязательные поля формы');
        return;
    }

    const submitButton = document.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    // Отправка данных на сервер
    fetch('/submit_appointment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            policy,
            specialist,
            date,
            time
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            closeModal();
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Ошибка:', error))
    .finally(() => {
        submitButton.disabled = false;
    });
}

// Закрытие модального окна при клике вне его
window.onclick = function(event) {
    const modal = document.getElementById('appointmentModal');
    if (event.target == modal) {
        closeModal();
    }
}

// Функция удаления выбранных записей
function deleteSelectedAppointments() {
    const selectedAppointments = document.querySelectorAll('input[name="selected_appointments"]:checked');
    const appointmentIds = Array.from(selectedAppointments).map(checkbox => checkbox.value);
    console.log('Selected appointment IDs:', appointmentIds);
    if (appointmentIds.length === 0) {
        alert('Пожалуйста, выберите хотя бы одну запись для удаления.');
        return;
    }

    console.log('Sending delete request for appointments:', appointmentIds);
    fetch('/delete_selected_appointments', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ appointmentIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Выбранные записи успешно удалены.');
            location.reload();
        } else {
            alert('Ошибка при удалении записей.');
        }
    })
    .catch(error => console.error('Ошибка:', error));
}

// Функция редактирования поля пользователя
function editField(field, userId) {
    console.log(`Редактирование поля ${field} для пользователя с ID ${userId}`);
    // Здесь можно добавить логику для открытия модального окна или инлайн-редактирования
    alert(`Редактирование поля ${field} для пользователя с ID ${userId}`);
}

// Инициализация после загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM загружен, инициализация скрипта");
    
    // Находим все кнопки записи
    const appointmentButtons = document.querySelectorAll('.cta-button');
    console.log("Найдено кнопок записи:", appointmentButtons.length);
    
    // Добавляем обработчики для каждой кнопки
    appointmentButtons.forEach(button => {
        const onclickAttr = button.getAttribute('onclick');
        if (onclickAttr && onclickAttr.includes('openModal')) {
            button.addEventListener('click', function(e) {
                e.preventDefault(); // Предотвращаем стандартное поведение
                const match = onclickAttr.match(/'([^']+)'/);
                if (match) {
                    const doctorType = match[1];
                    console.log("Клик по кнопке записи к врачу:", doctorType);
                    openModal(doctorType);
                }
            });
        }
    });
    
    // Инициализация формы
    const form = document.getElementById('appointmentForm');
    if (form) {
        form.addEventListener('submit', submitForm);
    }
    
    // Инициализация временных слотов
    generateTimeSlots();
});
