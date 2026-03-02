import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ImagesTableComponent } from './images-table.component';

describe('ImagesTableComponent', () => {
  let component: ImagesTableComponent;
  let fixture: ComponentFixture<ImagesTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImagesTableComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ImagesTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
