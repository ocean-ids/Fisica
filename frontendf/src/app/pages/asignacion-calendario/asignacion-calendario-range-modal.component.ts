import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

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
    MatButtonModule
  ],
  templateUrl: './asignacion-calendario-range-modal.component.html',
  styleUrl: './asignacion-calendario-range-modal.component.css'
})
export class AsignacionCalendarioRangeModalComponent {
  start: string;
  end: string;
  seq: string;
  errorText: string = '';
  previewRows: Array<{ label: string; date: string; dayKey: string; currentValue: string; newValue: string }> = [];
  rowTitle: string = '';

  constructor(
    private dialogRef: MatDialogRef<AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult>,
    @Inject(MAT_DIALOG_DATA) public data: AsignacionRangeModalData
  ) {
    this.start = data.start || '';
    this.end = data.end || '';
    this.seq = data.seq || '';
    this.rowTitle = this.buildRowTitle(data?.row);
    this.refreshPreview();
  }

  onInputChange(): void {
    this.refreshPreview();
  }

  cancel(): void {
    this.dialogRef.close();
  }

  submit(): void {
    this.errorText = '';
    if (!this.start || !this.end || !this.seq) {
      this.errorText = 'Completa desde, hasta y secuencia.';
      return;
    }

    const startDate = new Date(this.start + 'T00:00:00');
    const endDate = new Date(this.end + 'T00:00:00');
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      this.errorText = 'Fechas inválidas.';
      return;
    }
    if (startDate > endDate) {
      this.errorText = 'La fecha final debe ser mayor o igual a la inicial.';
      return;
    }

    const currentYear = new Date().getFullYear();
    if (startDate.getFullYear() !== currentYear || endDate.getFullYear() !== currentYear) {
      this.errorText = 'El rango debe estar dentro del año actual.';
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
      end: this.end,
      seq: this.seq
    });
  }

  private isValidSequence(seq: string, isSacafranco: boolean): boolean {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return false;
    if (isSacafranco) return true;
    return /[FDN]/.test(raw);
  }

  private refreshPreview(): void {
    this.previewRows = [];
    const startDate = this.parseDate(this.start);
    const endDate = this.parseDate(this.end);
    if (!startDate || !endDate) return;
    if (startDate > endDate) return;

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

  private parseSequence(seq: string, isSacafranco: boolean): string[] {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return [];
    if (!isSacafranco) {
      return raw.match(/[FDN]/g) || [];
    }
    const parts = raw.split(/[^A-Z0-9]+/).filter(Boolean);
    return parts.length ? parts : [raw];
  }

  private parseDate(value: string): Date | null {
    if (!value) return null;
    const d = new Date(value + 'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
  }

  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private formatLabel(d: Date): string {
    const shortOrder = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];
    const dow = d.getDay();
    const dayNum = String(d.getDate()).padStart(2, '0');
    return `${shortOrder[dow]}${dayNum}`;
  }

  private dayKeyFromDate(dateStr: string): string {
    if (!dateStr) return '';
    const parts = dateStr.split('-').map(Number);
    if (parts.length !== 3) return '';
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    const map = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    return map[d.getDay()];
  }

  private buildRowTitle(row: any): string {
    if (!row) return '';
    const puestoNombre = row?.puesto_detalle?.nombre || row?.puesto_detalle?.tipo || '';
    const personaNombre = row?.persona_nombre || row?.persona || '';
    const parts = [puestoNombre, personaNombre].filter(Boolean);
    return parts.join(' · ');
  }
}
