import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import {Persona} from '../../models/persona.model'
import { PersonaService } from '../../services/persona.service';
import { PersonaFormComponent } from './persona-form/persona-form.component';
import Swal from 'sweetalert2';
import { ViewChild, ElementRef } from '@angular/core';
import { saveAs } from 'file-saver';
import { Subscription } from 'rxjs';
import { Router } from '@angular/router';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';

@Component({
  selector: 'app-personas',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule, MatSlideToggleModule],
  templateUrl: './personas.component.html',
  styleUrl: './personas.component.css'
})
export class PersonasComponent implements OnInit, OnDestroy {
  personas: Persona[] = [];

  isImporting = false;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  filtroTexto = '';
  private filterSub?: Subscription;
  filtroTipo = '';
  tipos = [ 'FIJOS', 'RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAFRANCO', 'SACAVACACIONES', 'SUPERVISOR ZONAL', 'SUPERVISOR MOTORIZADO', 'SUPERVISOR DE ACOMPAÑAMIENTO' ];

  constructor(
    private personaService: PersonaService,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router
  ){}

  ngOnInit(): void {
   this.cargarPersonas();
   this.filterSub = this.globalFilter.state$.subscribe(state => {
    if (!this.router.url.startsWith('/dashboard/personas')) return;
    this.filtroTexto = state.query || '';
    this.cargarPersonas();
   })
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  cargarPersonas(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroTipo) params.tipo = this.filtroTipo;
    this.personaService.getPersonas(params).subscribe({
      next: data => this.personas = data,
      error: err => console.error('Error al cargar', err)
    });
  }


  limpiarFiltros(): void {
    this.filtroTexto = '';
    this.filtroTipo = '';
    this.cargarPersonas();
  }

  abrirModal(persona?: Persona): void {
    const dialogRef = this.dialog.open(PersonaFormComponent, {
      width: '500px',
      data: persona || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (persona?.id) {
          this.actualizarPersona(persona.id, result);
        } else {
          this.crearPersona(result);
        }
      }
    });
  }

  crearPersona(data: any): void {
    this.personaService.createPersona(data).subscribe({
      next: () => {
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Creada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al crear persona:', error);
        const msg = error?.error?.error || 'No se pudo crear';
        Swal.fire({ icon: 'warning', title: 'Duplicado', text: msg });
      }
    });
  }

  actualizarPersona(id: number, data: any): void {
    this.personaService.updatePersona(id, data).subscribe({
      next: () => {
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Actualizada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al actualizar persona:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' });
      }
    });
  }

  async confirmarEliminar(persona: Persona): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar persona?',
      text: `Se eliminará ${persona.nombres} ${persona.apellidos}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed || !persona.id) return;

    this.personaService.deletePersona(persona.id).subscribe({
      next: () => {
        this.cargarPersonas();
        Swal.fire({ icon: 'success', title: 'Eliminada', timer: 1200, showConfirmButton: false });
      },
      error: (error) => {
        console.error('Error al eliminar persona:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' });
      }
    });
  }

  toggleActive(persona: Persona, checked: boolean): void {
    if (!persona?.id) return;
    const id = persona.id;
    if (checked) {
      this.personaService.enablePersona(id).subscribe({
        next: () => { persona.is_active = true; },
        error: (err) => {
          console.error('Error habilitando persona', err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo habilitar' });
        }
      });
    } else {
      this.personaService.disablePersona(id).subscribe({
        next: () => { persona.is_active = false; },
        error: (err) => {
          console.error('Error deshabilitando persona', err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo deshabilitar' });
        }
      });
    }
  }


  dispararImportacion() {
    this.fileInput.nativeElement.value = '';
    this.fileInput.nativeElement.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files[0];
    if (!file) return;
    this.isImporting = true;
    this.personaService.importPersonas(file).subscribe({
      next: (res) => {
        this.cargarPersonas();
        const errores = Array.isArray(res?.errores) ? res.errores : [];
        const errs = errores.length ? `<br/>Errores: ${errores.length}` : '';
        const erroresHtml = errores.length
          ? `<div style="text-align:left;max-height:220px;overflow:auto;margin-top:8px;">
                <strong>Detalle de errores:</strong>
                <ul style="margin:6px 0 0 18px;">${errores.map((e: any) => {
                  if (e && typeof e === 'object') {
                    const fila = e.fila ?? '';
                    const msg = e.error ?? JSON.stringify(e);
                    return `<li>Fila ${fila}: ${msg}</li>`;
                  }
                  return `<li>${String(e)}</li>`;
                }).join('')}</ul>
             </div>`
          : '';
        Swal.fire({
          icon: res?.errores?.length ? 'warning' : 'success',
          title: 'Importación de personas',
          html: `Filas: ${res?.total_filas||0}<br/>Válidas: ${res?.filas_validas||0}<br/>Creadas: ${res?.creadas||0}<br/>Actualizadas: ${res?.actualizadas||0}${errs}${erroresHtml}`,
        });
        if (res?.errores?.length) console.warn('Errores importación', res.errores);
      },
      error: (err) => {
        const msg = err?.error?.error || 'No se pudo importar personas';
        Swal.fire({ icon: 'error', title: 'Importación falló', text: msg });
      },
      complete: () => {
        this.isImporting = false;
        this.fileInput.nativeElement.value = '';
      }
    });
  }

  descargarExcel(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroTipo) params.tipo = this.filtroTipo;
    this.personaService.exportPersonasExcel(params).subscribe({
      next: (blob) => {
        const fecha = new Date().toISOString().slice(0, 10);
        saveAs(blob, `personas_${fecha}.xlsx`);
      },
      error: () => {
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo descargar el Excel' });
      }
    });
  }

}
