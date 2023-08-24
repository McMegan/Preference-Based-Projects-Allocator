const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
const tooltipList = [...tooltipTriggerList].map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl));

const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
const popoverList = [...popoverTriggerList].map((popoverTriggerEl) => new bootstrap.Popover(popoverTriggerEl));

const toggle_info = (project_id) => {
	$(`.project_info[data-project-id="${project_id}"]`).slideToggle();
	$(`#project-${project_id} .project_info_toggle_button`).toggleClass('open');
};

const fix_striped_tables = () => {
	$('table.table-striped,table.table-striped-fixed').each((index, striped_table) => {
		striped_table = $(striped_table);
		if (striped_table.find('tr.project_info_container, tr.d-none').length && striped_table.find('tr.empty-form, tr:not(.empty-form) > [type="hidden"]').length <= 1) {
			// remove striped class from table
			striped_table.removeClass('table-striped');
			striped_table.addClass('table-striped-fixed');
			// find visible rows and add stripe
			striped_table.find('> tbody > tr:not(.project_info_container):not(.d-none)').each((index, row) => {
				row = $(row);
				row.removeClass('stripe');
				if (index % 2 == 0) row.addClass('stripe');
			});
		}
	});
};

const toggle_sidebar = () => {
	$('#sidebar').slideToggle();
	$('#sidebar_container').toggleClass('col-md-4');
	$('#sidebar_container').toggleClass('col-lg-3');
	$('#sidebar_container').toggleClass('col-md-1');
	$('#sidebar_container').toggleClass('col-lg-1');
};

window.onload = () => {
	fix_striped_tables();
};
