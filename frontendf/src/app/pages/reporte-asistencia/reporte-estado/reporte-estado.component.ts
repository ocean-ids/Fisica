import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheetRef } from '@angular/material/bottom-sheet';
import { MatButtonModule } from '@angular/material/button';
import { ResumenAsistencia } from '../../../models';

@Component({
  selector: 'app-reporte-estado',
  imports: [CommonModule, MatButtonModule],
  templateUrl: './reporte-estado.component.html',
  styleUrl: './reporte-estado.component.css'
})
export class ReporteEstadoComponent {

  constructor(
    @Inject(MAT_BOTTOM_SHEET_DATA) public data: ResumenAsistencia,
    private bottomSheetRef: MatBottomSheetRef<ReporteEstadoComponent>
  ) {}

  close(): void {
    this.bottomSheetRef.dismiss();
  }

}
