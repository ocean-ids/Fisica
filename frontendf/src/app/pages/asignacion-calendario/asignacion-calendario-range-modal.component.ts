import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import {MatCheckboxModule} from '@angular/material/checkbox';

export interface AsignacionRangeModalData {
  start: string;
  end: string;
  seq: string;
  isSacafranco: boolean;
  weekStart?: string;
  row?: any;
}

export interface AsignacionRangeModalResult {
  start: string;
  end: string;
  seq: string;
}

@Component({
  selector: 'app-asignacion-calendario-range-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule
  ],
  templateUrl: './asignacion-calendario-range-modal.component.html',
  styleUrl: './asignacion-calendario-range-modal.component.css'
})
export class AsignacionCalendarioRangeModalComponent {
  private readonly NO_END_MONTHS = 24;
  start: string;
  end: string;
  seq: string;
  noEnd = false;
  errorText: string = '';
  previewRows: Array<{ label: string; date: string; dayKey: string; currentValue: string; newValue: string }> = [];
  rowTitle: string = '';

  constructor(
    private dialogRef: MatDialogRef<AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult>,
    @Inject(MAT_DIALOG_DATA) public data: AsignacionRangeModalData
  ) {
    this.start = data.start || '';
    this.seq = data.seq || '';
    // "Sin fecha fin" marcado por defecto: arranca sin fecha de fin.
    this.noEnd = true;
    this.end = '';
    this.rowTitle = this.buildRowTitle(data?.row);
    this.refreshPreview();
  }

  // Maneja el cambio de la opcion hasta"
  onInputChange(): void { 
    this.refreshPreview();
  }

  // Cierra el modal y devuelve los datos ingresados
  cancel(): void {
    this.dialogRef.close();
  }

  openDatePicker(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    if (!input) return;
    if (typeof input.showPicker === 'function') {
      input.showPicker();
    } else {
      input.focus();
    }
  }

  submit(): void {
    this.errorText = '';
    if (!this.start || !this.seq) {
      this.errorText = 'Completa desde y secuencia.';
      return;
    }

    const startDate = this.parseDate(this.start);
    const endDate = this.getEndDate();
    if (!startDate || !endDate) {
      this.errorText = 'Fechas inválidas.';
      return;
    }
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      this.errorText = 'Fechas inválidas.';
      return;
    }
    if (startDate > endDate) {
      this.errorText = 'La fecha final debe ser mayor o igual a la inicial.';
      return;
    }

    if (!this.isValidSequence(this.seq, this.data.isSacafranco)) {
      this.errorText = this.data.isSacafranco
        ? 'Ingresa una secuencia válida.'
        : 'Solo se permiten F, D o N.';
      return;
    }

    this.dialogRef.close({
      start: this.start,
      end: this.formatDateLocal(endDate),
      seq: this.seq
    });
  }

  // Maneja el cambio del checkbox "Sin fecha de fin" 
  onNoEndChange(): void {
    if (this.noEnd) {
      this.end = '';
    }
    this.onInputChange();
  }

  // Maneja el cambio del campo "Hasta" para desactivar la opción "Sin fecha de fin" si se ingresa una fecha
  onEndChange(): void {
    if (this.end){
      this.noEnd = false;
    }
    this.onInputChange();
  }

  // Obtiene la fecha de fin considerando la opción "Sin fecha de fin"
  private getEndDate(): Date | null {
    const startDate = this.parseDate(this.start);
    if (!startDate) return null;

    if (this.noEnd) {
      const end = new Date(startDate);
      // Keep a finite horizon to avoid flooding the API with thousands of weekly saves.
      end.setMonth(end.getMonth() + this.NO_END_MONTHS);
      end.setDate(end.getDate() - 1);
      return end;
    }

    return this.parseDate(this.end);
  }

  // Valida la secuencia ingresada, permitiendo cualquier valor si es sacafranco o solo F/D/N si no lo es
  private isValidSequence(seq: string, isSacafranco: boolean): boolean {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return false;
    if (isSacafranco) return true;
    return /[FDN]/.test(raw);
  }
  
  // Refresca la vista previa de los cambios basándose en las fechas y secuencia ingresadas
  private refreshPreview(): void {
    this.previewRows = [];
    const startDate = this.parseDate(this.start);
    let endDate = this.getEndDate();
    if (!startDate || !endDate) return;
    if (startDate > endDate) return;

    if (this.noEnd) {
      const y = startDate.getFullYear();
      const m = startDate.getMonth();
      const monthEnd = new Date(y, m + 1, 0);
      if (monthEnd < endDate) endDate = monthEnd;
    }

    const tokens = this.parseSequence(this.seq, this.data.isSacafranco);
    const row = this.data?.row || {};
    let idx = 0;
    const d = new Date(startDate);
    while (d <= endDate) {
      const dateStr = this.formatDateLocal(d);
      const label = this.formatLabel(d);
      const dayKey = this.dayKeyFromDate(dateStr);
      const currentValue = (row && dayKey ? (row[dayKey] || '') : '').toString().toUpperCase();
      const newValue = tokens.length ? tokens[idx % tokens.length] : '';
      this.previewRows.push({
        label,
        date: dateStr,
        dayKey,
        currentValue,
        newValue
      });
      idx += 1;
      d.setDate(d.getDate() + 1);
    }
  }

  // Parsea la secuencia ingresada en un arreglo de tokens
  private parseSequence(seq: string, isSacafranco: boolean): string[] {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return [];
    if (!isSacafranco) {
      return raw.match(/[FDN]/g) || [];
    }
    const parts = raw.split(/[^A-Z0-9]+/).filter(Boolean);
    return parts.length ? parts : [raw];
  }

  // Convierte una fecha en formato string a un objeto Date, considerando solo la parte de la fecha
  private parseDate(value: string): Date | null {
    if (!value) return null;
    const d = new Date(value + 'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
  }

  // Formatea una fecha a formato YYYY-MM-DD para usar en los campos de fecha
  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // Formatea una fecha para mostrarla en la vista previa
  private formatLabel(d: Date): string {
    const shortOrder = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];
    const dow = d.getDay();
    const dayNum = String(d.getDate()).padStart(2, '0');
    return `${shortOrder[dow]}${dayNum}`;
  }

  // Obtiene la clave del día de la semana a partir de una fecha en formato string
  private dayKeyFromDate(dateStr: string): string {
    if (!dateStr) return '';
    const parts = dateStr.split('-').map(Number);
    if (parts.length !== 3) return '';
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    const map = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    return map[d.getDay()];
  }

  // Construye el título de una fila basándose en los detalles del puesto y la persona
  private buildRowTitle(row: any): string {
    if (!row) return '';
    const puestoNombre = row?.puesto_detalle?.nombre || row?.puesto_detalle?.tipo || '';
    const personaNombre = row?.persona_nombre || row?.persona || '';
    const parts = [puestoNombre, personaNombre].filter(Boolean);
    return parts.join(' · ');
  }
}
