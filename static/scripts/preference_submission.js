const fix_up_down_arrows = () => {
	// Disable up arrow for first preference & down arrow for last preference
	let up_arrows = $('.project_move_up_preference');
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
	let down_arrows = $('.project_move_down_preference');
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

const update_add_remove_button = (project_id, show_add = true) => {
	// Disable add button / enable remove button
	let project_add_button = $(`[data-project-id="${project_id}"] .add_project_to_prefs`);
	if (show_add) {
		project_add_button.removeClass('disabled');
		project_add_button.removeClass('d-none');
		project_add_button.attr('aria-disabled', 'false');
	} else {
		project_add_button.addClass('disabled');
		project_add_button.addClass('d-none');
		project_add_button.attr('aria-disabled', 'true');
	}

	let project_remove_button = $(`[data-project-id="${project_id}"] .remove_project_from_prefs`);
	if (!show_add) {
		project_remove_button.removeClass('disabled');
		project_remove_button.removeClass('d-none');
		project_remove_button.attr('aria-disabled', 'false');
	} else {
		project_remove_button.addClass('disabled');
		project_remove_button.addClass('d-none');
		project_remove_button.attr('aria-disabled', 'true');
	}
};

const add_project_to_prefs = (project_id) => {
	let initial_form_count = +$('#id_form-INITIAL_FORMS').val();
	let min_form_count = +$('#id_form-MIN_NUM_FORMS').val();

	// Find number of preferences currently in form
	let form_count = +$('#id_form-TOTAL_FORMS').val();

	let rank = form_count + 1;
	for (let i = initial_form_count; i < min_form_count; i++) {
		if ($(`input#id_form-${i}-rank`).val() == '') {
			rank = i + 1;
			break;
		}
	}

	// Grab current project row
	let project_row = $(`#project_table .project_row[data-project-id="${project_id}"]`);
	project_row.addClass('d-none');
	project_row = project_row.clone();
	project_row.removeClass('d-none');
	project_row.removeClass('stripe');
	project_row.removeClass('project_row');
	project_row.addClass('preference_row');
	project_row.attr('data-rank', rank);

	project_row.find('td.project_capacity').remove();

	// Add preference stuff
	project_row.prepend(`
        <td scope="row">
            <div class="d-flex gap-1">
                <button type="button"onclick="move_preference(${project_id})" class="project_move_up_preference border-0 btn btn-sm p-0"><i class="bi bi-arrow-up"></i></button>
                <button type="button" onclick="move_preference(${project_id}, false)" class="project_move_down_preference border-0 btn btn-sm p-0"><i class="bi bi-arrow-down"></i></button>
            </div>
        </td>
        <td class="preference_rank text-center">${rank}</td>
    `);

	// Grab project info
	let project_info = $(`#project_table .project_info_container[data-project-id="${project_id}"]`);
	project_info.addClass('d-none');
	project_info = project_info.clone();
	project_info.removeClass('d-none');

	// Append to preference list
	$('#preference_table > tbody').append(project_row);
	$('#preference_table > tbody').append(project_info);

	// Disable add button / enable remove button
	update_add_remove_button(project_id, false);

	// Find first empty form -> if none then clone emtpy form
	let new_form = $(`input#id_form-${rank - 1}-rank`);
	if (new_form.length) {
		new_form = new_form.parents('tr');
		console.log(new_form);
		new_form.find(`input#id_form-${rank - 1}-rank`)[0].setAttribute('value', rank);
		new_form.find(`input#id_form-${rank - 1}-project_id`)[0].setAttribute('value', project_id);
	} else {
		new_form = $('.preference-submission-form tr.empty-form').prop('outerHTML');
		new_form = new_form.replace('d-none empty-form', '');
		new_form = new_form.replaceAll('__prefix__', rank - 1);
		new_form = $(new_form);
		new_form.find(`input#id_form-${rank - 1}-rank`)[0].setAttribute('value', rank);
		new_form.find(`input#id_form-${rank - 1}-project_id`)[0].setAttribute('value', project_id);

		// Append to form
		$('.preference-submission-form tbody').append(new_form);
	}

	// Update TOTAL_FORMS to match new form count
	$('#id_form-TOTAL_FORMS').val(rank);

	fix_up_down_arrows();
	fix_striped_tables();
};

const remove_project_from_prefs = (project_id) => {
	// Remove from preference list
	let preference_row = $(`.preference_row[data-project-id="${project_id}"]`);
	preference_row.remove();

	// Grab preference count & rank
	let preference_count = +$('#id_form-TOTAL_FORMS').val();
	let current_rank = +preference_row.attr('data-rank');

	// Fix project info
	let preference_project_info = $(`#preference_table .project_info_container[data-project-id="${project_id}"]`);
	preference_project_info.remove();
	let project_info = $(`#project_table .project_info_container[data-project-id="${project_id}"]`);
	project_info.removeClass('d-none');

	// Remove from forms
	let form_row = $(`#id_form-${current_rank - 1}-rank`).parent();
	form_row.remove();

	// Update projects list
	let project_row = $(`.project_row[data-project-id="${project_id}"]`);
	project_row.removeClass('d-none');
	update_add_remove_button(project_id);

	// Update ranks
	for (let rank = current_rank + 1; rank < preference_count + 1; rank++) {
		// Update preference list
		let preference_row = $(`.preference_row[data-rank="${rank}"]`);
		preference_row.attr('data-rank', rank - 1);
		preference_row.find('.preference_rank').text(rank - 1);
		// Update form
		let preference_form = $(`#id_form-${rank - 1}-rank`).parent('tr');
		let new_preference_form = preference_form.prop('outerHTML');
		new_preference_form = new_preference_form.replaceAll(`form-${rank - 1}-`, `form-${rank - 2}-`);
		new_preference_form = $(new_preference_form);
		new_preference_form.find(`input#id_form-${rank - 2}-rank`)[0].setAttribute('value', rank - 1);
		preference_form.replaceWith(new_preference_form);
	}

	// Update preference form count
	$('#id_form-TOTAL_FORMS').val(preference_count - 1);

	fix_up_down_arrows();
	fix_striped_tables();
};

const move_preference = (project_id, move_up = true) => {
	// Move the current preference up or down

	// Swap in preference list
	let current_preference_row = $(`.preference_row[data-project-id="${project_id}"]`);
	let current_rank = +current_preference_row.attr('data-rank');
	let swap_rank = current_rank + (move_up ? -1 : 1);

	let swap_preference_row = $(`.preference_row[data-rank="${swap_rank}"]`);

	current_preference_row.attr('data-rank', swap_rank);
	swap_preference_row.attr('data-rank', current_rank);

	current_preference_row.find('.preference_rank').text(swap_rank);
	swap_preference_row.find('.preference_rank').text(current_rank);

	// Swap in forms
	let current_preference_form = $(`#id_form-${current_rank - 1}-rank`).parent('tr');
	let swap_preference_form = $(`#id_form-${swap_rank - 1}-rank`).parent('tr');

	let new_current_preference_form = current_preference_form.prop('outerHTML');
	new_current_preference_form = new_current_preference_form.replaceAll(`form-${current_rank - 1}-`, `form-${swap_rank - 1}-`);
	new_current_preference_form = $(new_current_preference_form);
	new_current_preference_form.find(`input#id_form-${swap_rank - 1}-rank`)[0].setAttribute('value', swap_rank);
	current_preference_form.replaceWith(new_current_preference_form);

	let new_swap_preference_form = swap_preference_form.prop('outerHTML');
	new_swap_preference_form = new_swap_preference_form.replaceAll(`form-${swap_rank - 1}-`, `form-${current_rank - 1}-`);
	new_swap_preference_form = $(new_swap_preference_form);
	new_swap_preference_form.find(`input#id_form-${current_rank - 1}-rank`)[0].setAttribute('value', current_rank);
	swap_preference_form.replaceWith(new_swap_preference_form);

	// Swap
	if (move_up) {
		swap_preference_row.before(current_preference_row);
		new_swap_preference_form.before(new_current_preference_form);
	} else {
		current_preference_row.before(swap_preference_row);
		new_current_preference_form.before(new_swap_preference_form);
	}

	fix_up_down_arrows();
	fix_striped_tables();
};

window.onload = () => {
	fix_up_down_arrows();
	fix_striped_tables();

	$('input.project-search').each((index, elem) => {
		let field = $(elem).data()['field'];
		$(elem).on('keyup', (event) => {
			var search = $(elem).val().toLowerCase();
			$(`#project_table > tbody > tr .project_${field}`).filter((index, elem) => {
				$(elem)
					.closest('tr')
					.toggle($(elem).text().toLowerCase().indexOf(search) > -1);
			});
			fix_striped_tables();
		});
	});
};
