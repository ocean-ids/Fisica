import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { PersonalConsola } from '../../models';
import { PersonalConsolaService } from '../../services/personal-consola.service';
import { PersonalConsolaFormComponent } from './personal-consola-form/personal-consola-form.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-personal-consola',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatSlideToggleModule],
  templateUrl: './personal-consola.component.html',
  styleUrl: './personal-consola.component.css'
})
export class PersonalConsolaComponent implements OnInit {
  lista: PersonalConsola[] = [];
  filtroTurno = '';

  constructor(
    private svc: PersonalConsolaService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    const params: any = {};
    if (this.filtroTurno) params.turno = this.filtroTurno;
    this.svc.getPersonalConsola(params).subscribe({
      next: data => this.lista = data || [],
      error: err => console.error('Error al cargar personal consola:', err) 
    });
  }

  abrirModal(item?: PersonalConsola): void {
    const dialogRef = this.dialog.open(PersonalConsolaFormComponent, {
      width: '600px',
      data: item || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;

      if (item?.id) {
        this.svc.updatePersonalConsola(item.id, result).subscribe({
          next: () => {
            this.cargar();
            Swal.fire({ icon: 'success', title: 'Actualizado', timer: 1200, showConfirmButton: false });
          },
          error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' })
        });
      } else {
        this.svc.createPersonalConsola(result).subscribe({
          next: () => {
            this.cargar();
            Swal.fire({ icon: 'success', title: 'Creado', timer: 1200, showConfirmButton: false });
          },
          error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear' })
        });
      }
    });
  }

  eliminar(item: PersonalConsola): void {
    Swal.fire({
      title: '¿Eliminar registro?',
      text: `${item.apellidos} ${item.nombres}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    }).then(res => {
      if (!res.isConfirmed || !item.id) return;
      this.svc.deletePersonalConsola(item.id).subscribe({
        next: () => {
          this.cargar();
          Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1200, showConfirmButton: false });
        },
        error: () => Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' })
      });
    });
  }

  toggleActivo(item: PersonalConsola, checked: boolean): void {
    if (!item.id) return;
    const estadoAnterior = item.is_active;

    this.svc.updatePersonalConsola(item.id, { is_active: checked }).subscribe({
      next: () => {
        item.is_active = checked;
      },
      error: () => {
        item.is_active = estadoAnterior;
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar estado' });
      }
    });
  }
}
