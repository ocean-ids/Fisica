import { Component, OnInit, Output, EventEmitter, Input, OnChanges, SimpleChanges } from '@angular/core';
import { AsignacionSemanal, SacafrancoFilaSemanal } from '../../models/asignacion-calendario';
import { SacafrancoFila } from '../../models/asignacion.model';
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';
import { PuestoService } from '../../services/puesto.service';
import { AsignacionService } from '../../services/asignacion.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { PatronAsignacionService } from '../../services/patron-asignacion.service';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult } from './asignacion-calendario-range-modal.component';


@Component({
  selector: 'app-asignacion-calendario',
  standalone: true,
  imports: [FormsModule, CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './asignacion-calendario.component.html',
  styleUrl: './asignacion-calendario.component.css'
})
export class AsignacionCalendarioComponent implements OnInit, OnChanges{
  @Input() weekStart: string = '';
  @Input() filterText: string = '';
  @Input() rowOrder: Array<number | string> = [];
  @Input() sacafrancoRows: SacafrancoFila[] = [];
  @Output() sacafrancoClick: EventEmitter<any> = new EventEmitter<any>();
    ngOnChanges(changes: SimpleChanges): void {
      if (changes['weekStart'] && !changes['weekStart'].firstChange) {
        this.loadWeek();
      }
      if (changes['filterText'] && !changes['filterText'].firstChange) {
        this.loadWeek();
      }
      if (changes['rowOrder'] && !changes['rowOrder'].firstChange) {
        this.applyOrder();
      }
      if (changes['sacafrancoRows'] && !changes['sacafrancoRows'].firstChange) {
        this.buildDisplayRows();
      }
    }
  weeks: string[] = [];
  currentWeekIndex: number = 0;
  weekDays: Array<{short:string, name:string, date:string, dayNum:number}> = [];
  rows: any[] = [];
  displayRows: any[] = [];
  loading = false;
  @Input() allowCreateEmptyRows: boolean = false;

  sacafrancoWeekRows: SacafrancoFilaSemanal[] = [];
  

 
  sacafrancoPreview: { [puestoId: string]: { [day: string]: string } } = {};

  constructor(
    private asignacionCalendarioService: AsignacionCalendarioService,
    private puestoService: PuestoService,
    private asignacionService: AsignacionService,
    private patronAsignacionService: PatronAsignacionService,
    private dialog: MatDialog
  ){}

  ngOnInit(): void {
    
    if (!this.weekStart) {
      this.weekStart = this.computeCurrentMonthStart();
    }

    console.log('AsignacionCalendario ngOnInit weekStart=', this.weekStart);
    this.loadWeek();
  }

  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }


  computeCurrentMonthStart(): string{
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}-01`;
  }

  loadWeek(){
  
    this.computeWeekDays();
    this.loading = true;
    const params: any = { week_start: this.weekStart, auto_create: true };
    if (this.filterText && this.filterText.trim()) {
      params.q = this.filterText.trim();
    }
    this.asignacionCalendarioService.obtenerAsignacionesCalendario(params)
      .subscribe({
        next: (res: any) => {
        if (Array.isArray(res)) {
          this.rows = res;
        } else if (res && Array.isArray(res.results)) {
          this.rows = res.results;
        } else {
          this.rows = [];
        }

        this.applyOrder();
        this.loadSacafrancoWeek();

        
        console.log('loadWeek result for', this.weekStart, 'res=', res);
        if((!this.rows || this.rows.length === 0)){
          const parts = (this.weekStart||'').split('-').map(Number);
          const base = (parts.length===3) ? new Date(parts[0], parts[1]-1, parts[2]) : new Date();
          const mes = base.getMonth() + 1;
          const anio = base.getFullYear();
          // Si no hay filas semanales en la base, solo mostramos filas vacías por puesto
          // cuando `allowCreateEmptyRows` está habilitado. De lo contrario dejamos la tabla vacía.
          if (this.allowCreateEmptyRows) {
            this.puestoService.getPuestos().subscribe({ next: (puestos: any) => {
              const fullRows = (puestos||[]).map((p:any)=> ({ puesto: p.id, puesto_detalle: p, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' }));
              this.rows = fullRows;
            }});
          } else {
            this.rows = [];
          }
          this.buildDisplayRows();
        }
          this.loading = false;
          
          try { this.weekStartChange.emit(this.weekStart); } catch(e){}
        },
        error: () => this.loading = false
      });
  }

  private loadSacafrancoWeek(): void {
    if (!this.weekStart) {
      this.sacafrancoWeekRows = [];
      this.buildDisplayRows();
      return;
    }
    this.asignacionCalendarioService.obtenerSacafrancoFilaSemanal({ week_start: this.weekStart })
      .subscribe({
        next: data => {
          this.sacafrancoWeekRows = data || [];
          this.buildDisplayRows();
        },
        error: () => {
          this.sacafrancoWeekRows = [];
          this.buildDisplayRows();
        }
      });
  }

  private getRowOrderKey(row: any): string {
    if (row?._sacafranco) {
      return `sacafranco-${row?._sacafrancoId ?? ''}`;
    }
    const key = row?.asignacion || row?.asignacion_id || row?.puesto || '';
    return String(key);
  }

  private applyOrder(): void {
    this.buildDisplayRows();
  }

  private buildDisplayRows(): void {
    const sacafrancoRows = this.buildSacafrancoRows();
    const combined = [...(this.rows || []), ...sacafrancoRows];
    if (!combined.length) {
      this.displayRows = [];
      return;
    }

    if (this.rowOrder && this.rowOrder.length) {
      const orderMap = new Map<string, number>();
      this.rowOrder.forEach((id, idx) => orderMap.set(String(id), idx));
      combined.sort((a, b) => {
        const aKey = this.getRowOrderKey(a);
        const bKey = this.getRowOrderKey(b);
        const aIdx = orderMap.get(aKey);
        const bIdx = orderMap.get(bKey);
        const aHas = aIdx !== undefined;
        const bHas = bIdx !== undefined;
        if (aHas && bHas) return (aIdx as number) - (bIdx as number);
        if (aHas) return -1;
        if (bHas) return 1;
        return 0;
      });
    }

    this.displayRows = combined;
  }

  private buildSacafrancoRows(): any[] {
    if (!this.sacafrancoRows || !this.sacafrancoRows.length || !this.weekStart) return [];
    const parts = this.weekStart.split('-').map(Number);
    if (parts.length !== 3) return [];
    const month = parts[1];
    const year = parts[0];
    const currentKey = (year * 12) + month;
    const weekMap = new Map<number, SacafrancoFilaSemanal>();
    (this.sacafrancoWeekRows || []).forEach(r => {
      if (r?.sacafranco_fila) weekMap.set(r.sacafranco_fila, r);
    });
    return (this.sacafrancoRows || [])
      .filter(r => {
        const rowMonth = Number(r.mes) || 0;
        const rowYear = Number(r.anio) || 0;
        const rowKey = (rowYear * 12) + rowMonth;
        return rowKey > 0 && rowKey <= currentKey;
      })
      .sort((a, b) => (a.orden ?? 0) - (b.orden ?? 0))
      .map(r => {
        const week = weekMap.get(r.id as number);
        return {
          _sacafranco: true,
          _sacafrancoId: r.id,
          mon: week?.mon || '',
          tue: week?.tue || '',
          wed: week?.wed || '',
          thu: week?.thu || '',
          fri: week?.fri || '',
          sat: week?.sat || '',
          sun: week?.sun || ''
        };
      });
  }

  loadWeeksForMonth(mes: number, anio: number){
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }

    this.weeks = weeksLocal;
    const idx = this.weeks.indexOf(this.weekStart);
    this.currentWeekIndex = idx >= 0 ? idx : 0;
    if (this.weeks.length){
      this.weekStart = this.weeks[this.currentWeekIndex] || this.weeks[0];
    } else {
      this.weekStart = '';
    }
    this.loadWeek();
  }

  prevWeek(){
    if(this.currentWeekIndex > 0){
      this.currentWeekIndex -= 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
  }

  nextWeek(){
    if(this.currentWeekIndex < this.weeks.length - 1){
      this.currentWeekIndex += 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
  }

        @Output() weekStartChange: EventEmitter<string> = new EventEmitter<string>();

  saveRow(row: any){
    const asignacionId = row.asignacion || row.asignacion_id;
    if (!asignacionId) {
      // Evita crear filas semanales huerfanas sin asignacion padre.
      return;
    }

    const payload: any = {
    puesto: row.puesto || (row.puesto_detalle && row.puesto_detalle.id),
    week_start: this.weekStart,
    mon: row.mon || '',
    tue: row.tue || '',
    wed: row.wed || '',
    thu: row.thu || '',
    fri: row.fri || '',
    sat: row.sat || '',
    sun: row.sun || ''
  };
  payload.asignacion_id = asignacionId;
  this.asignacionCalendarioService.crearAsignacionCalendario(payload)
    .subscribe({
      next: () => {},
      error: () => {}
    });
  }
  

  onCellChange(row: any, day: string, value: any){
    const v = value ? String(value).toUpperCase().slice(0,4) : '';
    row[day] = v;
    this.saveRow(row);
  }

  onSacafrancoCellChange(row: any, day: string, value: any){
    const raw = value ? String(value).toUpperCase() : '';
    const tokens = raw
      .split(/[\s,;]+/)
      .map(t => t.replace(/[^A-Z0-9]/g, '').slice(0, 5))
      .filter(t => t.length > 0);

    const weekKeys = this.weekDays
      .filter(d => d.date)
      .map(d => this.dayKeyFromDate(d.date))
      .filter(k => k);

    const startIdx = weekKeys.indexOf(day);
    if (startIdx === -1) return;

    const daysToSave: string[] = [];
    if (tokens.length > 1) {
      tokens.forEach((t, idx) => {
        const key = weekKeys[startIdx + idx];
        if (!key) return;
        row[key] = t;
        daysToSave.push(key);
      });
    } else {
      const v = tokens.length ? tokens[0] : '';
      for (let i = startIdx; i < weekKeys.length; i += 1) {
        const key = weekKeys[i];
        row[key] = v;
        daysToSave.push(key);
      }
    }

    if (daysToSave.length) {
      this.saveSacafrancoRow(row, daysToSave);
    }
  }

  private saveSacafrancoRow(row: any, days: string[]): void {
    const filaId = row?._sacafrancoId;
    if (!filaId) return;
    const payload: any = {
      sacafranco_fila: filaId,
      week_start: this.weekStart
    };
    days.forEach(d => {
      payload[d] = row[d] || '';
    });
    this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload)
      .subscribe({ next: () => {}, error: () => {} });
  }

  getCellClass(value: string){
    if(!value) return '';
    const v = value.toString().toUpperCase();
    if(v.startsWith('F')) return 'cell-franco';
    if(v.startsWith('D')) return 'cell-dia';
    if(v.startsWith('N')) return 'cell-noche';
    if(v.startsWith('DS') || v.startsWith('NS')) return 'cell-desc';
    if(v.startsWith('MA') || v.startsWith('MI')) return 'cell-daycode';
    return '';
  }

  dayKeyFromDate(dateStr: string): string {
   
    if(!dateStr) return '';
    try {
      const parts = dateStr.split('-').map(Number);
      if (parts.length !== 3) return '';
      const d = new Date(parts[0], parts[1]-1, parts[2]);
      const map = ['sun','mon','tue','wed','thu','fri','sat'];
      return map[d.getDay()];
    } catch (e) {
      return '';
    }
  }
  
  computeWeekDays(): void {
    this.weekDays = [];
    if (!this.weekStart) return;
    const parts = this.weekStart.split('-').map(Number);
    if (parts.length !== 3) return;
    const base = new Date(parts[0], parts[1]-1, parts[2]);
    const baseMonth = base.getMonth();
    const shortOrder = ['Do','Lu','Ma','Mi','Ju','Vi','Sá'];
    const fullOrder = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

    for (let i = 0; i < 7; i++){
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const dow = d.getDay();
      const inMonth = d.getMonth() === baseMonth;
      this.weekDays.push({
        short: shortOrder[dow],
        name: fullOrder[dow],
        date: inMonth ? this.formatDateLocal(d) : '',
        dayNum: inMonth ? d.getDate() : 0
      });
    }
  }

  private _clickTimer: any = null;

  handleCellClick(event: MouseEvent, row: any, day: string, puestoId: any) {
    event.stopPropagation();
   
    if (this._clickTimer) return;
    this._clickTimer = setTimeout(() => {
      this._clickTimer = null;
      this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: false });
    }, 250);
  }

  handleCellDblClick(event: MouseEvent, row: any, day: string, puestoId: any) {
    event.stopPropagation();
    if (this._clickTimer) {
      clearTimeout(this._clickTimer);
      this._clickTimer = null;
    }
    this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: true });
  }

  openRangeModal(row: any, dayKey: string, isSacafranco: boolean): void {
    const clickedDate = this.getDateForDayKey(this.weekStart, dayKey);
    if (!clickedDate) return;
    const startDefault = this.formatDateLocal(clickedDate);
    const endDefault = this.formatDateLocal(clickedDate);
    const ref = this.dialog.open(AsignacionCalendarioRangeModalComponent, {
      width: '420px',
      data: {
        start: startDefault,
        end: endDefault,
        seq: '',
        isSacafranco
      }
    });

    ref.afterClosed().subscribe((result?: AsignacionRangeModalResult) => {
      if (!result) return;
      const { start, end, seq } = result;
      if (!start || !end || !seq) return;

      const startDate = new Date(start + 'T00:00:00');
      const endDate = new Date(end + 'T00:00:00');
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return;

      const tokens = this.parseSequence(seq, isSacafranco);
      if (!tokens.length) return;

      const anchor = this.parseWeekStart(this.weekStart);
      const rangeMap = this.buildRangeMap(startDate, endDate, tokens, anchor);
      this.applyRangeToBackend(row, rangeMap, isSacafranco);
      this.applyRangeToCurrentWeek(row, rangeMap);
    });
  }

  private parseSequence(seq: string, isSacafranco: boolean): string[] {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return [];
    if (!isSacafranco) {
      const letters = raw.match(/[FDN]/g) || [];
      return letters;
    }
    const parts = raw.split(/[\s,]+/).filter(Boolean);
    return parts.length ? parts : [raw];
  }

  private buildRangeMap(startDate: Date, endDate: Date, tokens: string[], anchorWeekStart?: Date | null): Record<string, Record<string, string>> {
    const map: Record<string, Record<string, string>> = {};
    let idx = 0;
    const d = new Date(startDate);
    const anchorStart = anchorWeekStart ? new Date(anchorWeekStart) : null;
    const anchorEnd = anchorStart ? new Date(anchorStart) : null;
    if (anchorEnd) anchorEnd.setDate(anchorEnd.getDate() + 6);
    while (d <= endDate) {
      const weekStart = (anchorStart && anchorEnd && d >= anchorStart && d <= anchorEnd)
        ? anchorStart
        : this.getWeekStartForDate(d);
      const weekKey = this.formatDateLocal(weekStart);
      const dayKey = this.dayKeyFromDate(this.formatDateLocal(d));
      if (!map[weekKey]) map[weekKey] = {};
      map[weekKey][dayKey] = tokens[idx % tokens.length];
      idx += 1;
      d.setDate(d.getDate() + 1);
    }
    return map;
  }

  private parseWeekStart(weekStartStr: string): Date | null {
    if (!weekStartStr) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  private getWeekStartForDate(d: Date): Date {
    const y = d.getFullYear();
    const m = d.getMonth();
    const day = d.getDate();
    const startDay = 1 + Math.floor((day - 1) / 7) * 7;
    return new Date(y, m, startDay);
  }

  private getDateForDayKey(weekStartStr: string, dayKey: string): Date | null {
    if (!weekStartStr || !dayKey) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    const base = new Date(parts[0], parts[1] - 1, parts[2]);
    for (let i = 0; i < 7; i++) {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      if (this.dayKeyFromDate(this.formatDateLocal(d)) === dayKey) return d;
    }
    return null;
  }

  private applyRangeToBackend(row: any, rangeMap: Record<string, Record<string, string>>, isSacafranco: boolean): void {
    const keys = Object.keys(rangeMap);
    keys.forEach(weekStart => {
      const days = rangeMap[weekStart] || {};
      if (!Object.keys(days).length) return;
      if (isSacafranco) {
        const filaId = row?._sacafrancoId;
        if (!filaId) return;
        const payload: any = { sacafranco_fila: filaId, week_start: weekStart };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload).subscribe({ next: () => {}, error: () => {} });
      } else {
        const asignacionId = row?.asignacion || row?.asignacion_id;
        if (!asignacionId) return;
        const payload: any = {
          asignacion_id: asignacionId,
          puesto: row.puesto || (row.puesto_detalle && row.puesto_detalle.id),
          week_start: weekStart
        };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        this.asignacionCalendarioService.crearAsignacionCalendario(payload).subscribe({ next: () => {}, error: () => {} });
      }
    });
  }

  private applyRangeToCurrentWeek(row: any, rangeMap: Record<string, Record<string, string>>): void {
    const weekDays = rangeMap[this.weekStart] || {};
    Object.keys(weekDays).forEach(k => {
      row[k] = weekDays[k];
    });
  }

  showPreview(puestoId: any, day: string) {
    try {
      const key = String(puestoId || '');
      this.sacafrancoPreview[key] = this.sacafrancoPreview[key] || {};  
      if (this.sacafrancoPreview[key][day]) return;

      this.patronAsignacionService.getSacafrancos(this.weekStart, day, puestoId)
        .subscribe({
          next: (list: any[]) => {
            const assigned = (list || []).find(p => p.assigned_for_puesto || p.status === 'assigned');
            if (assigned) {
              this.sacafrancoPreview[key][day] = (assigned.nombre || assigned.first_name || '') + (assigned.apellidos ? (' ' + assigned.apellidos) : '');
            } else {
              this.sacafrancoPreview[key][day] = 'Sin asignar';
            }
          },
          error: () => { this.sacafrancoPreview[key][day] = ''; }
        });
    } catch (e) {}
  }

  clearPreview(puestoId: any, day: string) {
    const key = String(puestoId || '');
    if (this.sacafrancoPreview[key]) this.sacafrancoPreview[key][day] = '';
  }

  getPreviewTitle(puestoId: any, day: string) {
    const key = String(puestoId || '');
    return (this.sacafrancoPreview[key] && this.sacafrancoPreview[key][day]) || '';
  }

  onInfoClick(event: MouseEvent, puestoId: any, day: string) {
    event.stopPropagation();
    
    this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: true });
  }

}
