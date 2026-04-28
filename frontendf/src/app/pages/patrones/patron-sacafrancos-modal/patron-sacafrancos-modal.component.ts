import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { PatronAsignacionService } from '../../../services/patron-asignacion.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-patron-sacafrancos-modal',
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, MatButtonModule, MatChipsModule, MatDialogModule, MatProgressSpinnerModule],
  templateUrl: './patron-sacafrancos-modal.component.html',
  styleUrl: './patron-sacafrancos-modal.component.css'
})
export class PatronSacafrancosModalComponent {
  lista: any[] = [];
  weekStart?: string;
  day?: string;
  selected: any = null;
  loading: boolean = false;

  constructor(
    public dialogRef: MatDialogRef<PatronSacafrancosModalComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    private patronService: PatronAsignacionService
  ) {
    this.lista = data?.lista || [];
    this.weekStart = data?.weekStart;
    this.day = data?.day;
    // preselect the person assigned to this puesto (if any)
    try {
      this.selected = this.lista.find((p: any) => Number(p.assigned_for_puesto) === Number(p.id)) || null;
    } catch (e) {
      this.selected = null;
    }
  }

  close(): void {
    this.dialogRef.close();
  }

  // keep selection in modal; user must press Asignar/Quitar
  onSelect(event: any) {
    this.selected = event?.value;
  }

  asignar() {
    if (!this.selected || !this.weekStart || !this.day) return;
    this.loading = true;
    const payload = {
      persona_id: this.selected.id,
      puesto_id: this.data.puestoId || this.data.puestoId,
      week_start: this.weekStart,
      day: this.day,
      value: 'S'
    };
    this.patronService.asignarSacafranco(payload).subscribe({
      next: (res) => { this.loading = false; this.dialogRef.close({ action: 'assigned', result: res }); },
      error: (err) => {
        this.loading = false;
        console.error('Error asignando', err);
        Swal.fire({
          icon: 'warning',
          title: 'Sacafranco ocupado',
          text: this.getErrorMessage(err) || 'La persona ya esta asignada en otro puesto'
        });
      }
    });
  }

  desasignar() {
    if (!this.selected || !this.weekStart || !this.day) return;
    this.loading = true;
    const payload = {
      persona_id: this.selected.id,
      puesto_id: this.data.puestoId || this.data.puestoId,
      week_start: this.weekStart,
      day: this.day
    };
    this.patronService.desasignarSacafranco(payload).subscribe({
      next: (res) => { this.loading = false; this.dialogRef.close({ action: 'unassigned', result: res }); },
      error: (err) => { this.loading = false; console.error('Error desasignando', err); }
    });
  }

  displayStatus(status: string|undefined|null) {
    if (!status) { return ''; }
    const s = status.toString().toLowerCase();
    if (s === 'available') { return 'Disponible'; }
    if (s === 'assigned' || s === 'asignado') { return 'Asignado'; }
    
    return status.toString();
  }

  getChipColor(status: string|undefined|null) {
    if (!status) { return '';
    }
    return status.toString().toLowerCase() === 'available' ? 'primary' : 'warn';
  }

  private getErrorMessage(err: any): string {
    if (!err) return '';
    return err?.error?.error || err?.error?.detail || err?.message || '';
  }
}
