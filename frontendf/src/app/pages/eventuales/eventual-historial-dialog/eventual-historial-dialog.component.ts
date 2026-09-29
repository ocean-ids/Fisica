import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { HorasEventualService } from '../../../services/horas-eventual.service';
import { HorasEventual, HorasEventualHistorialItem } from '../../../models/horas-eventual.model';

interface DialogData {
  row: HorasEventual;
}

// Historial de un registro de horas: quién lo creó, quién lo modificó y qué cambió.
@Component({
  selector: 'app-eventual-historial-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './eventual-historial-dialog.component.html',
  styleUrl: './eventual-historial-dialog.component.css',
})
export class EventualHistorialDialogComponent implements OnInit {
  items: HorasEventualHistorialItem[] = [];
  cargando = false;
  error = '';

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private srv: HorasEventualService,
  ) {}

  ngOnInit(): void {
    const id = this.data?.row?.id;
    if (!id) { return; }
    this.cargando = true;
    this.srv.historial(id).subscribe({
      next: (rows) => { this.items = rows || []; this.cargando = false; },
      error: () => { this.error = 'No se pudo cargar el historial.'; this.cargando = false; },
    });
  }

  // ¿Este campo cambió en esta versión respecto a la anterior? (se resalta)
  cambio(it: HorasEventualHistorialItem, etiqueta: string): boolean {
    return (it.cambios || []).includes(etiqueta);
  }

  fechaDMA(v: string | null): string {
    if (!v) { return ''; }
    const [y, m, d] = String(v).slice(0, 10).split('-');
    return (y && m && d) ? `${d}/${m}/${y}` : String(v);
  }
}
