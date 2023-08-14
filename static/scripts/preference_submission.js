const fix_up_down = () => {
	// Disable up arrow for first preference & down arrow for last preference
	let up_arrows = document.querySelectorAll('.preference_move_up:not(#preference-__prefix__-move-up)');
	for (let i = 0; i < up_arrows.length; i++) {
		let arrow = up_arrows[i];
		if (i == 0) {
			arrow.classList.add('disabled');
			arrow.classList.add('opacity-25');
			arrow.setAttribute('aria-disabled', 'true');
		} else {
			arrow.classList.remove('disabled');
			arrow.classList.remove('opacity-25');
			arrow.removeAttribute('aria-disabled');
		}
	}
	let down_arrows = document.querySelectorAll('.preference_move_down:not(#preference-__prefix__-move-down)');
	for (let i = 0; i < down_arrows.length; i++) {
		let arrow = down_arrows[i];
		if (i == down_arrows.length - 1) {
			arrow.classList.add('disabled');
			arrow.classList.add('opacity-25');
			arrow.setAttribute('aria-disabled', 'true');
		} else {
			arrow.classList.remove('disabled');
			arrow.classList.remove('opacity-25');
			arrow.removeAttribute('aria-disabled');
		}
	}
};

const update_form_index = (element, currentIndex, newIndex) => {
	// Set id for new preference
	element.id = 'preference-' + newIndex;
	// Set on-click behaviour
	let remove_button = element.querySelector('#preference-' + currentIndex + '-remove');
	remove_button.id = 'preference-' + newIndex + '-remove';
	remove_button.setAttribute('onclick', 'remove_preference(' + newIndex + ')');
	// Update preference index
	element.querySelector('.preference_index').innerHTML = newIndex + 1;
	// Update ids & names
	let div_id = element.querySelector('#div_id_form-' + currentIndex + '-project');
	div_id.id = 'div_id_form-' + newIndex + '-project';
	let select_id = element.querySelector('#id_form-' + currentIndex + '-project');
	select_id.id = 'id_form-' + newIndex + '-project';
	let select_name = element.querySelector('[name="form-' + currentIndex + '-project"]');
	select_name.name = 'form-' + newIndex + '-project';

	let up_id = element.querySelector('#preference-' + currentIndex + '-move-up');
	up_id.id = 'preference-' + newIndex + '-move-up';
	let down_id = element.querySelector('#preference-' + currentIndex + '-move-down');
	down_id.id = 'preference-' + newIndex + '-move-down';
};

const add_preference = () => {
	// Find number of preferences currently in form
	let preference_count = +document.getElementsByName('form-TOTAL_FORMS')[0].value;
	// Clone last preference in form
	let new_preference = document.querySelector('#preference_form_table_body .empty-form').cloneNode(true);
	update_form_index(new_preference, '__prefix__', preference_count);
	// Set classlist
	new_preference.classList = ['preference_form'];
	// Add new preference form to page
	document.getElementById('preference_form_table_body').append(new_preference);
	// Update TOTAL_FORMS to match new form count
	document.getElementsByName('form-TOTAL_FORMS')[0].value = preference_count + 1;

	fix_up_down();
};

const remove_preference = (preference_index) => {
	// Iterate through each form after the removed form
	let preference_forms = document.getElementsByClassName('preference_form');
	for (let i = preference_index + 1; i < preference_forms.length; i++) {
		update_form_index(preference_forms[i], i, i - 1);
	}
	// Remove preference row
	document.getElementById('preference-' + preference_index).remove();
	// Update TOTAL_FORMS to match new form count
	document.getElementsByName('form-TOTAL_FORMS')[0].value = document.getElementsByName('form-TOTAL_FORMS')[0].value - 1;

	fix_up_down();
};

const move_preference = (preference_index, move_up = true) => {
	// Move the current preference up or down
	console.log(preference_index);
	console.log(move_up ? 'up' : 'down');

	fix_up_down();
};

window.onload = () => {
	document.getElementsByName('add_preference')[0].onclick = add_preference;
	fix_up_down();
};
